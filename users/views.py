from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout, get_backends
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm  # Make sure you have this
from rest_framework_simplejwt.tokens import RefreshToken
import uuid
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.chains.question_answering import load_qa_chain
import os
from django.utils import timezone

os.environ["GROQ_API_KEY"] = "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"


class ChatbotView(TemplateView):
    template_name = "chatbot2.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['theme'] = self.request.GET.get('theme', 'Dark')
        context['file_uploaded'] = bool(self.request.session.get('faiss_index_path'))
        context['uploaded_filename'] = self.request.session.get('original_filename', '')
        # Add chat history to context
        context['chat_history'] = self.request.session.get('chat_history', [])
        return context
    
    def post(self, request):
        context = self.get_context_data()
        
        try:
            if 'pdf_file' in request.FILES:
                self._handle_file_upload(request)
                context['file_uploaded'] = True
                context['uploaded_filename'] = request.session.get('original_filename', '')
                # Clear chat history when new file is uploaded
                if 'chat_history' in request.session:
                    del request.session['chat_history']
                request.session.modified = True
            
            if 'user_query' in request.POST:
                # Get or initialize chat history
                chat_history = request.session.get('chat_history', [])
                
                # Add user message to history
                user_query = request.POST['user_query']
                chat_history.append({
                    'sender': 'user',
                    'message': user_query,
                    'time': timezone.now().strftime("%H:%M")
                })
                
                # Get bot response
                bot_response = self._handle_user_query(request)
                
                # Add bot response to history
                chat_history.append({
                    'sender': 'bot',
                    'message': bot_response,
                    'time': timezone.now().strftime("%H:%M")
                })
                
                # Save updated history to session
                request.session['chat_history'] = chat_history
                context['chat_history'] = chat_history
                
        except Exception as e:
            context['error'] = str(e)
            
        return self.render_to_response(context)
    
    def _handle_file_upload(self, request):
        # Generate unique index name
        index_name = f"faiss_index_{uuid.uuid4().hex}"
        index_path = os.path.join("vectorstores", index_name)
        
        # Create directories if they don't exist
        os.makedirs("vectorstores", exist_ok=True)
        os.makedirs("uploads", exist_ok=True)
        
        # Save uploaded file
        file = request.FILES['pdf_file']
        file_path = os.path.join("uploads", file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Process PDF
        with open(file_path, 'rb') as pdf_file:
            pdf_pages = PdfReader(pdf_file)
            text = "".join(page.extract_text() or "" for page in pdf_pages.pages)
        
        if not text.strip():
            raise ValueError("PDF text extraction failed - no text found")
        
        # Split text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)
        
        # Create embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        
        # Create and save vector store
        vector_store = FAISS.from_texts(chunks, embeddings)
        vector_store.save_local(index_path)
        
        # Store path and filename in session
        request.session['faiss_index_path'] = index_path
        request.session['original_filename'] = file.name
    
    def _handle_user_query(self, request):
        index_path = request.session.get('faiss_index_path')
        if not index_path or not os.path.exists(index_path):
            raise ValueError("Please upload a PDF file first")
        
        # Load embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        
        # Load vector store
        vector_store = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        
        # Process query
        query = request.POST['user_query']
        docs = vector_store.similarity_search(query, k=3)
        
        # Generate response
        llm = ChatGroq(
            model_name="llama3-8b-8192",
            temperature=0.7
        )
        chain = load_qa_chain(llm, chain_type="stuff")
        result = chain({"input_documents": docs, "question": query})
        
        return result['output_text']
    

class RegisterView(View):
    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, 'registration/register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            backend = get_backends()[0]  # use the first configured backend
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            return redirect('home')
        return render(request, 'registration/register.html', {'form': form})


class LoginView(View):
    def get(self, request):
        form = AuthenticationForm()
        return render(request, 'registration/login.html', {'form': form})

    def post(self, request):
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Optional: JWT Token (if using in frontend)
            refresh = RefreshToken.for_user(user)
            # store in session or return in JSON
            request.session['access_token'] = str(refresh.access_token)

            next_url = request.GET.get('next') or reverse_lazy('home')
            return redirect(next_url)
        return render(request, 'registration/login.html', {'form': form})


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')
