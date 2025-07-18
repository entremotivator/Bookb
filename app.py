import streamlit as st
import streamlit.components.v1 as components
import base64
import requests
import json
import time
from datetime import datetime
import re
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import ebooklib
from ebooklib import epub
import zipfile
import tempfile
import os

# Hardcoded webhook URL
HARDCODED_WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook-test/61e8b566-40c1-4925-940b-c6e74b9563cc"

# Page configuration
st.set_page_config(
    page_title="📚 Book Buddy - Complete Edition", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False
if 'auto_send_audio' not in st.session_state:
    st.session_state.auto_send_audio = None
if 'webhook_response' not in st.session_state:
    st.session_state.webhook_response = None
if 'book_content' not in st.session_state:
    st.session_state.book_content = ""
if 'book_metadata' not in st.session_state:
    st.session_state.book_metadata = {
        'title': '',
        'author': '',
        'genre': '',
        'isbn': '',
        'publisher': '',
        'year': '',
        'description': ''
    }
if 'google_doc_url' not in st.session_state:
    st.session_state.google_doc_url = ""
if 'live_content' not in st.session_state:
    st.session_state.live_content = ""
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None

# Sidebar navigation
st.sidebar.title("📚 Book Buddy Navigation")
page = st.sidebar.radio(
    "Choose a page:",
    ["🎙️ Voice Chat", "📝 Book Formatter", "📄 PDF/EPUB Generator", "🌐 Google Docs Live", "⚙️ Settings"],
    key="page_selector"
)

# Common sidebar settings
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 Global Settings")
webhook_url = st.sidebar.text_input("Additional Webhook URL (Optional)", placeholder="https://your-n8n-instance.com/webhook/book-buddy")
auto_send = st.sidebar.checkbox("Auto-send after recording", value=True)
show_json = st.sidebar.checkbox("Show webhook responses", value=False)

# Show hardcoded webhook info
st.sidebar.markdown("### 🔗 Primary Webhook")
st.sidebar.info(f"🎯 **Auto-send to:**\n{HARDCODED_WEBHOOK_URL}")

# Book type options
book_types = [
    "Fiction", "Non-Fiction", "Biography", "Mystery", "Romance", 
    "Science Fiction", "Fantasy", "Thriller", "Historical Fiction",
    "Self-Help", "Business", "Educational", "Poetry", "Children's Book",
    "Academic", "Technical", "Memoir", "Essay Collection", "Other"
]

def send_audio_to_webhook(audio_base64, user_name, book_type, prompt_text, source="voice_recording"):
    """Send audio data to the hardcoded webhook"""
    try:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "user_name": user_name,
            "book_type": book_type,
            "prompt": prompt_text,
            "audio_data": audio_base64,
            "audio_format": "audio/webm",
            "source": source,
            "app_version": "Book Buddy Complete Edition"
        }
        
        response = requests.post(HARDCODED_WEBHOOK_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            st.session_state.webhook_response = response.json() if response.text else {"status": "success"}
            st.session_state.messages.append({
                "type": source,
                "user": user_name,
                "book_type": book_type,
                "prompt": prompt_text,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "status": "sent"
            })
            return True, "Audio sent successfully!"
        else:
            return False, f"Webhook returned status code: {response.status_code}"
            
    except Exception as e:
        return False, f"Error sending audio: {str(e)}"

def create_voice_recorder():
    """Create the enhanced voice recorder component with auto-send"""
    recorder_html = f"""
    <div id="voice-recorder" style="text-align: center; padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; margin: 20px 0; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
        <h3 style="color: white; margin-bottom: 20px; text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">🎙️ Voice Recorder</h3>
        
        <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px; margin-bottom: 20px;">
            <p style="color: white; margin: 0; font-size: 14px;">🎯 Auto-sends to: {HARDCODED_WEBHOOK_URL[:50]}...</p>
        </div>
        
        <button id="recordButton" style="
            background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
            color: white;
            border: none;
            padding: 18px 36px;
            font-size: 18px;
            border-radius: 30px;
            cursor: pointer;
            margin: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
            font-weight: bold;
        ">🎙️ Start Recording</button>
        
        <button id="stopButton" disabled style="
            background: linear-gradient(45deg, #666, #888);
            color: white;
            border: none;
            padding: 18px 36px;
            font-size: 18px;
            border-radius: 30px;
            cursor: pointer;
            margin: 10px;
            transition: all 0.3s ease;
            font-weight: bold;
        ">⏹️ Stop Recording</button>
        
        <div id="status" style="
            margin: 25px 0;
            font-size: 20px;
            font-weight: bold;
            color: white;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        ">📚 Ready to capture your book thoughts</div>
        
        <div id="waveform" style="
            width: 100%;
            height: 80px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            margin: 25px 0;
            display: none;
            position: relative;
            overflow: hidden;
        "></div>
        
        <div id="recordingStats" style="
            color: white;
            font-size: 14px;
            margin: 10px 0;
            display: none;
        ">
            <span id="duration">00:00</span> | <span id="fileSize">0 KB</span>
        </div>
        
        <audio id="audioPlayback" controls style="
            width: 100%;
            margin: 25px 0;
            display: none;
            border-radius: 10px;
        "></audio>
        
        <div id="sendingStatus" style="
            color: white;
            font-size: 16px;
            margin: 15px 0;
            display: none;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        "></div>
        
        <textarea id="base64output" style="display: none;"></textarea>
    </div>

    <script>
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let recordingTimer;
    let seconds = 0;
    let audioContext;
    let analyser;
    let dataArray;
    let animationId;

    const recordBtn = document.getElementById("recordButton");
    const stopBtn = document.getElementById("stopButton");
    const statusText = document.getElementById("status");
    const playback = document.getElementById("audioPlayback");
    const base64output = document.getElementById("base64output");
    const waveform = document.getElementById("waveform");
    const recordingStats = document.getElementById("recordingStats");
    const durationSpan = document.getElementById("duration");
    const fileSizeSpan = document.getElementById("fileSize");
    const sendingStatus = document.getElementById("sendingStatus");

    function updateButtonStyles() {{
        if (isRecording) {{
            recordBtn.style.background = "linear-gradient(45deg, #666, #888)";
            recordBtn.style.cursor = "not-allowed";
            recordBtn.style.transform = "scale(0.95)";
            stopBtn.style.background = "linear-gradient(45deg, #ff4757, #ff6b6b)";
            stopBtn.style.cursor = "pointer";
            stopBtn.style.boxShadow = "0 6px 20px rgba(255, 71, 87, 0.4)";
            stopBtn.style.transform = "scale(1.05)";
        }} else {{
            recordBtn.style.background = "linear-gradient(45deg, #ff6b6b, #ff8e8e)";
            recordBtn.style.cursor = "pointer";
            recordBtn.style.transform = "scale(1)";
            recordBtn.style.boxShadow = "0 6px 20px rgba(255, 107, 107, 0.4)";
            stopBtn.style.background = "linear-gradient(45deg, #666, #888)";
            stopBtn.style.cursor = "not-allowed";
            stopBtn.style.transform = "scale(0.95)";
        }}
    }}

    function startTimer() {{
        seconds = 0;
        recordingStats.style.display = 'block';
        recordingTimer = setInterval(() => {{
            seconds++;
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            durationSpan.textContent = `${{mins.toString().padStart(2, '0')}}:${{secs.toString().padStart(2, '0')}}`;
            statusText.innerHTML = `🔴 Recording... ${{mins}}:${{secs.toString().padStart(2, '0')}}`;
        }}, 1000);
    }}

    function stopTimer() {{
        clearInterval(recordingTimer);
        recordingStats.style.display = 'none';
    }}

    function drawWaveform() {{
        if (!analyser || !isRecording) return;
        
        analyser.getByteFrequencyData(dataArray);
        
        let bars = '';
        const barCount = 20;
        for(let i = 0; i < barCount; i++) {{
            const barHeight = (dataArray[i] / 255) * 60 + 10;
            bars += `<div style="
                position: absolute;
                bottom: 0;
                width: 3px;
                background: linear-gradient(to top, #ff6b6b, #ff8e8e);
                left: ${{(i / barCount) * 100}}%;
                height: ${{barHeight}}px;
                border-radius: 2px;
                transition: height 0.1s ease;
            "></div>`;
        }}
        waveform.innerHTML = bars;
        
        animationId = requestAnimationFrame(drawWaveform);
    }}

    async function sendAudioToWebhook(base64String) {{
        sendingStatus.style.display = 'block';
        sendingStatus.innerHTML = '📤 Sending audio to webhook...';
        
        try {{
            const payload = {{
                timestamp: new Date().toISOString(),
                audio_data: base64String,
                audio_format: 'audio/webm',
                source: 'voice_recording_auto',
                app_version: 'Book Buddy Complete Edition'
            }};
            
            const response = await fetch('{HARDCODED_WEBHOOK_URL}', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(payload)
            }});
            
            if (response.ok) {{
                sendingStatus.innerHTML = '✅ Audio sent successfully!';
                sendingStatus.style.background = 'rgba(76, 175, 80, 0.3)';
                
                // Notify Streamlit
                if (window.parent && window.parent.postMessage) {{
                    window.parent.postMessage({{
                        type: 'AUDIO_SENT_SUCCESS',
                        data: base64String
                    }}, '*');
                }}
            }} else {{
                throw new Error(`HTTP ${{response.status}}`);
            }}
        }} catch (error) {{
            sendingStatus.innerHTML = `❌ Failed to send: ${{error.message}}`;
            sendingStatus.style.background = 'rgba(244, 67, 54, 0.3)';
            
            // Notify Streamlit of error
            if (window.parent && window.parent.postMessage) {{
                window.parent.postMessage({{
                    type: 'AUDIO_SENT_ERROR',
                    error: error.message
                }}, '*');
            }}
        }}
        
        // Hide status after 5 seconds
        setTimeout(() => {{
            sendingStatus.style.display = 'none';
        }}, 5000);
    }}

    recordBtn.onclick = async () => {{
        try {{
            const stream = await navigator.mediaDevices.getUserMedia({{ 
                audio: {{
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100
                }}
            }});
            
            // Setup audio context for visualization
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            const source = audioContext.createMediaStreamSource(stream);
            source.connect(analyser);
            analyser.fftSize = 256;
            dataArray = new Uint8Array(analyser.frequencyBinCount);
            
            mediaRecorder = new MediaRecorder(stream, {{
                mimeType: 'audio/webm;codecs=opus'
            }});
            
            audioChunks = [];
            isRecording = true;
            
            mediaRecorder.ondataavailable = e => {{
                audioChunks.push(e.data);
                fileSizeSpan.textContent = `${{Math.round(e.data.size / 1024)}} KB`;
            }};
            
            mediaRecorder.onstop = async () => {{
                const blob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                const arrayBuffer = await blob.arrayBuffer();
                const base64String = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
                base64output.value = base64String;
                playback.src = URL.createObjectURL(blob);
                playback.style.display = 'block';
                statusText.innerHTML = "✅ Recording complete! 📚 Auto-sending to webhook...";
                waveform.style.display = 'none';
                
                // Auto-send to webhook
                await sendAudioToWebhook(base64String);
                
                stream.getTracks().forEach(track => track.stop());
                if (audioContext) {{
                    audioContext.close();
                }}
            }};

            mediaRecorder.start(100);
            startTimer();
            waveform.style.display = 'block';
            drawWaveform();
            recordBtn.disabled = true;
            stopBtn.disabled = false;
            updateButtonStyles();
            
        }} catch (err) {{
            statusText.innerHTML = "❌ Error: " + err.message;
            console.error('Error accessing microphone:', err);
        }}
    }};

    stopBtn.onclick = () => {{
        if (mediaRecorder && isRecording) {{
            mediaRecorder.stop();
            stopTimer();
            isRecording = false;
            recordBtn.disabled = false;
            stopBtn.disabled = true;
            updateButtonStyles();
            cancelAnimationFrame(animationId);
        }}
    }};

    updateButtonStyles();
    </script>

    <style>
    #voice-recorder button:hover {{
        transform: scale(1.05) !important;
        transition: all 0.2s ease;
    }}
    
    #voice-recorder button:active {{
        transform: scale(0.95) !important;
    }}
    
    @keyframes pulse {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
        100% {{ opacity: 1; }}
    }}
    
    #waveform {{
        animation: pulse 2s infinite;
    }}
    
    #sendingStatus {{
        animation: fadeIn 0.3s ease-in;
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
    </style>
    """
    return recorder_html

def format_text_for_book(text, style="novel"):
    """Format text according to book standards"""
    if not text:
        return ""
    
    # Clean up the text
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove extra blank lines
    text = re.sub(r'[ \t]+', ' ', text)  # Remove extra spaces
    
    if style == "novel":
        # Novel formatting
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            if para.strip():
                # Indent first line of each paragraph
                formatted_paragraphs.append(f"    {para.strip()}")
        
        return '\n\n'.join(formatted_paragraphs)
    
    elif style == "academic":
        # Academic formatting with citations
        text = re.sub(r'\b([A-Z][a-z]+)\s+(\d{4})\b', r'\1 (\2)', text)
        return text
    
    elif style == "poetry":
        # Poetry formatting
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip():
                formatted_lines.append(f"    {line.strip()}")
            else:
                formatted_lines.append("")
        
        return '\n'.join(formatted_lines)
    
    elif style == "screenplay":
        # Screenplay formatting
        text = re.sub(r'^([A-Z\s]+):(.*)$', r'\1\n\2', text, flags=re.MULTILINE)
        return text
    
    return text

def create_pdf(content, metadata, style="novel"):
    """Create a PDF from the content"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           leftMargin=1*inch, rightMargin=1*inch,
                          topMargin=1*inch, bottomMargin=1*inch)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.black,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    author_style = ParagraphStyle(
        'CustomAuthor',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        leftIndent=20 if style == "novel" else 0
    )
    
    story = []
    
    # Title page
    if metadata['title']:
        story.append(Paragraph(metadata['title'], title_style))
    if metadata['author']:
        story.append(Paragraph(f"by {metadata['author']}", author_style))
    
    if metadata['genre'] or metadata['year']:
        info_text = f"{metadata['genre']} | {metadata['year']}"
        story.append(Paragraph(info_text, author_style))
    
    story.append(Spacer(1, 50))
    
    # Description
    if metadata['description']:
        story.append(Paragraph(metadata['description'], body_style))
    
    story.append(Spacer(1, 30))
    story.append(PageBreak())
    
    # Content
    paragraphs = content.split('\n\n')
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), body_style))
            story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_epub(content, metadata):
    """Create an EPUB from the content"""
    book = epub.EpubBook()
    
    # Set metadata
    book.set_identifier(metadata.get('isbn', f'id_{int(time.time())}'))
    book.set_title(metadata.get('title', 'Untitled Book'))
    book.set_language('en')
    book.add_author(metadata.get('author', 'Unknown Author'))
    
    if metadata.get('description'):
        book.set_cover("image.jpg", open('cover.jpg', 'rb').read() if os.path.exists('cover.jpg') else b'')
    
    # Create chapter
    chapter = epub.EpubHtml(title='Chapter 1', file_name='chap_01.xhtml', lang='en')
    chapter.content = f'''
    <html>
    <head>
        <title>{metadata.get('title', 'Chapter 1')}</title>
    </head>
    <body>
        <h1>{metadata.get('title', 'Chapter 1')}</h1>
        {''.join(f'<p>{para}</p>' for para in content.split('\n\n') if para.strip())}
    </body>
    </html>
    '''
    
    book.add_item(chapter)
    
    # Define Table of Contents
    book.toc = (epub.Link("chap_01.xhtml", "Chapter 1", "chapter1"),)
    
    # Add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define CSS style
    style = 'body { font-family: Times, serif; margin: 40px; }'
    nav_css = epub.EpubItem(uid="nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)
    
    # Add spine
    book.spine = ['nav', chapter]
    
    # Create EPUB file
    buffer = io.BytesIO()
    epub.write_epub(buffer, book)
    buffer.seek(0)
    return buffer

def fetch_google_doc_content(url):
    """Fetch content from Google Docs"""
    try:
        # Convert Google Docs URL to export URL
        if '/document/d/' in url:
            doc_id = url.split('/document/d/')[1].split('/')[0]
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            
            response = requests.get(export_url)
            if response.status_code == 200:
                return response.text
        
        return None
    except Exception as e:
        st.error(f"Error fetching Google Doc: {str(e)}")
        return None

# Handle JavaScript messages from the voice recorder
def handle_js_messages():
    """Handle messages from JavaScript components"""
    # This would be handled by Streamlit's component communication
    pass

# PAGE 1: VOICE CHAT
if page == "🎙️ Voice Chat":
    st.title("🎙️ Voice Chat with Book Buddy")
    st.markdown("**Share your book thoughts through voice, audio files, or text!**")
    
    # Show hardcoded webhook info prominently
    st.info(f"🎯 **Audio recordings automatically send to:** `{HARDCODED_WEBHOOK_URL}`")
    
    # User input form
    col1, col2 = st.columns([1, 1])
    
    with col1:
        user_name = st.text_input("📝 Your Name", placeholder="Enter your name", value="Book Buddy User")
        book_type = st.selectbox("📚 Book Type", book_types, index=0)
    
    with col2:
        prompt_text = st.text_area("💭 Your Message/Question",
                                  placeholder="What would you like to discuss about books?",
                                 height=100,
                                 value="Voice recording from Book Buddy app")
    
    # File upload section
    st.markdown("### 📁 Upload Audio File")
    uploaded_file = st.file_uploader("Choose an audio file", type=['mp3', 'wav', 'ogg', 'webm', 'm4a'])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.audio(uploaded_file, format='audio/mp3')
        with col2:
            if st.button("🚀 Send Uploaded Audio", use_container_width=True):
                with st.spinner("📤 Sending to hardcoded webhook..."):
                    try:
                        audio_bytes = uploaded_file.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                        
                        success, message = send_audio_to_webhook(
                            audio_base64, user_name, book_type, prompt_text, "file_upload"
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
                            
                    except Exception as e:
                        st.error(f"💥 Error sending file: {str(e)}")
    
    st.markdown("---")
    
    # Voice recording section
    st.markdown("### 🎙️ Voice Recording")
    st.markdown("**🔄 Auto-send enabled:** Recordings will automatically be sent to the webhook after stopping.")
    
    recorder_component = components.html(create_voice_recorder(), height=500)
    
    # Text-only send option
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💬 Send Text Message", use_container_width=True, disabled=not user_name or not prompt_text):
            with st.spinner("📤 Sending text message to hardcoded webhook..."):
                try:
                    payload = {
                        "timestamp": datetime.now().isoformat(),
                        "user_name": user_name,
                        "book_type": book_type,
                        "prompt": prompt_text,
                        "source": "text_message",
                        "app_version": "Book Buddy Complete Edition"
                    }
                    
                    response = requests.post(HARDCODED_WEBHOOK_URL, json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        st.success("✅ Text message sent successfully!")
                        st.session_state.webhook_response = response.json() if response.text else {"status": "success"}
                        st.session_state.messages.append({
                            "type": "text",
                            "user": user_name,
                            "book_type": book_type,
                            "prompt": prompt_text,
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "status": "sent"
                        })
                        st.rerun()
                    else:
                        st.error(f"❌ Webhook Error: {response.status_code}")
                        
                except Exception as e:
                    st.error(f"💥 Error sending text: {str(e)}")
    
    with col2:
        if st.button("🗑️ Clear Message History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Display recent messages
    if st.session_state.messages:
        st.markdown("### 📋 Recent Messages")
        for i, msg in enumerate(st.session_state.messages[-10:]):
            status_icon = "✅" if msg.get('status') == 'sent' else "⏳"
            with st.expander(f"{status_icon} {msg['user']} - {msg['book_type']} ({msg['timestamp']})", expanded=False):
                st.write(f"**Type:** {msg['type'].title()}")
                st.write(f"**Message:** {msg['prompt']}")
                st.write(f"**Status:** {msg.get('status', 'unknown').title()}")
                if msg['type'] == 'upload':
                    st.write(f"**File:** {msg.get('filename', 'N/A')}")
    
    # Show webhook response
    if show_json and st.session_state.webhook_response:
        st.markdown("### 📄 Latest Webhook Response")
        with st.expander("Show JSON Response", expanded=False):
            st.json(st.session_state.webhook_response)

# PAGE 2: BOOK FORMATTER
elif page == "📝 Book Formatter":
    st.title("📝 Book Text Formatter")
    st.markdown("**Transform your raw text into properly formatted book content!**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### ✍️ Input Text")
        input_text = st.text_area("Paste your raw text here:", height=400, key="formatter_input")
        
        col1a, col1b = st.columns(2)
        with col1a:
            formatting_style = st.selectbox("📖 Formatting Style",
                                          ["novel", "academic", "poetry", "screenplay"],
                                          index=0)
        with col1b:
            if st.button("🎨 Format Text", use_container_width=True):
                if input_text:
                    formatted_text = format_text_for_book(input_text, formatting_style)
                    st.session_state.book_content = formatted_text
                    st.success("✅ Text formatted successfully!")
                    st.rerun()
    
    with col2:
        st.markdown("### 🔧 Formatting Options")
        
        # Advanced formatting options
        with st.expander("📚 Novel Formatting", expanded=True):
            st.markdown("""
            - Paragraph indentation
            - Proper spacing
            - Chapter breaks
            - Dialogue formatting
            """)
        
        with st.expander("🎓 Academic Formatting"):
            st.markdown("""
            - Citation formatting
            - Bibliography style
            - Footnote placement
            - Reference formatting
            """)
        
        with st.expander("🎭 Poetry Formatting"):
            st.markdown("""
            - Line spacing
            - Stanza breaks
            - Meter preservation
            - Indentation patterns
            """)
        
        with st.expander("🎬 Screenplay Formatting"):
            st.markdown("""
            - Character names
            - Scene descriptions
            - Dialogue formatting
            - Action lines
            """)
    
    # Display formatted text
    if st.session_state.book_content:
        st.markdown("### 📄 Formatted Output")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text_area("Formatted Text:", st.session_state.book_content, height=300, key="formatted_output")
        
        with col2:
            st.markdown("**📊 Statistics**")
            text = st.session_state.book_content
            word_count = len(text.split())
            char_count = len(text)
            para_count = len([p for p in text.split('\n\n') if p.strip()])
            
            st.metric("Words", word_count)
            st.metric("Characters", char_count)
            st.metric("Paragraphs", para_count)
            st.metric("Estimated Pages", max(1, word_count // 250))
        
        # Additional formatting tools
        st.markdown("### 🛠️ Additional Tools")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📝 Add Chapter Break", use_container_width=True):
                st.session_state.book_content += "\n\n" + "="*50 + "\nCHAPTER X\n" + "="*50 + "\n\n"
                st.rerun()
        
        with col2:
            if st.button("💭 Add Scene Break", use_container_width=True):
                st.session_state.book_content += "\n\n* * *\n\n"
                st.rerun()
        
        with col3:
            if st.button("🔤 Title Case", use_container_width=True):
                lines = st.session_state.book_content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and line.isupper():
                        lines[i] = line.title()
                st.session_state.book_content = '\n'.join(lines)
                st.rerun()
        
        with col4:
            if st.button("🧹 Clean Text", use_container_width=True):
                # Remove extra spaces and clean up
                text = st.session_state.book_content
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'\n\s*\n', '\n\n', text)
                st.session_state.book_content = text.strip()
                st.rerun()

# PAGE 3: PDF/EPUB GENERATOR
elif page == "📄 PDF/EPUB Generator":
    st.title("📄 PDF & EPUB Generator")
    st.markdown("**Create professional PDFs and EPUBs from your formatted text!**")
    
    # Book metadata form
    st.markdown("### 📋 Book Metadata")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.book_metadata['title'] = st.text_input("📖 Book Title", value=st.session_state.book_metadata['title'])
        st.session_state.book_metadata['author'] = st.text_input("✍️ Author", value=st.session_state.book_metadata['author'])
        st.session_state.book_metadata['genre'] = st.selectbox("📚 Genre", book_types, index=book_types.index(st.session_state.book_metadata['genre']) if st.session_state.book_metadata['genre'] in book_types else 0)
        st.session_state.book_metadata['isbn'] = st.text_input("🔢 ISBN", value=st.session_state.book_metadata['isbn'])
    
    with col2:
        st.session_state.book_metadata['publisher'] = st.text_input("🏢 Publisher", value=st.session_state.book_metadata['publisher'])
        st.session_state.book_metadata['year'] = st.text_input("📅 Year", value=st.session_state.book_metadata['year'])
        st.session_state.book_metadata['description'] = st.text_area("📝 Description", value=st.session_state.book_metadata['description'], height=100)
    
    # Content input
    st.markdown("### 📄 Book Content")
    if not st.session_state.book_content:
        st.session_state.book_content = st.text_area("Enter your book content here:", height=300, key="content_input")
    else:
        st.text_area("Book Content:", st.session_state.book_content, height=300, key="content_display")
    
    # Generation options
    st.markdown("### ⚙️ Generation Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pdf_style = st.selectbox("📄 PDF Style", ["novel", "academic", "poetry", "screenplay"], index=0)
    
    with col2:
        include_toc = st.checkbox("📑 Include Table of Contents", value=True)
    
    with col3:
        page_numbers = st.checkbox("🔢 Add Page Numbers", value=True)
    
    # Generate buttons
    st.markdown("### 🚀 Generate Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Generate PDF", use_container_width=True):
            if st.session_state.book_content and st.session_state.book_metadata['title']:
                with st.spinner("📄 Creating PDF..."):
                    try:
                        pdf_buffer = create_pdf(st.session_state.book_content, st.session_state.book_metadata, pdf_style)
                        
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{st.session_state.book_metadata['title']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("✅ PDF generated successfully!")
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
            else:
                st.warning("⚠️ Please provide book content and title")
    
    with col2:
        if st.button("📚 Generate EPUB", use_container_width=True):
            if st.session_state.book_content and st.session_state.book_metadata['title']:
                with st.spinner("📚 Creating EPUB..."):
                    try:
                        epub_buffer = create_epub(st.session_state.book_content, st.session_state.book_metadata)
                        
                        st.download_button(
                            label="⬇️ Download EPUB",
                            data=epub_buffer.getvalue(),
                            file_name=f"{st.session_state.book_metadata['title']}.epub",
                            mime="application/epub+zip",
                            use_container_width=True
                        )
                        st.success("✅ EPUB generated successfully!")
                    except Exception as e:
                        st.error(f"❌ Error generating EPUB: {str(e)}")
            else:
                st.warning("⚠️ Please provide book content and title")
    
    with col3:
        if st.button("📦 Generate Both", use_container_width=True):
            if st.session_state.book_content and st.session_state.book_metadata['title']:
                with st.spinner("📦 Creating both formats..."):
                    try:
                        # Generate PDF
                        pdf_buffer = create_pdf(st.session_state.book_content, st.session_state.book_metadata, pdf_style)
                        
                        # Generate EPUB
                        epub_buffer = create_epub(st.session_state.book_content, st.session_state.book_metadata)
                        
                        # Create download buttons
                        col_pdf, col_epub = st.columns(2)
                        
                        with col_pdf:
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"{st.session_state.book_metadata['title']}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        
                        with col_epub:
                            st.download_button(
                                label="⬇️ Download EPUB",
                                data=epub_buffer.getvalue(),
                                file_name=f"{st.session_state.book_metadata['title']}.epub",
                                mime="application/epub+zip",
                                use_container_width=True
                            )
                        
                        st.success("✅ Both formats generated successfully!")
                    except Exception as e:
                        st.error(f"❌ Error generating files: {str(e)}")
            else:
                st.warning("⚠️ Please provide book content and title")
    
    # Preview section
    if st.session_state.book_content:
        st.markdown("### 👀 Content Preview")
        
        with st.expander("📖 Book Preview", expanded=False):
            preview_text = st.session_state.book_content[:1000] + "..." if len(st.session_state.book_content) > 1000 else st.session_state.book_content
            st.text(preview_text)
            
            # Statistics
            word_count = len(st.session_state.book_content.split())
            char_count = len(st.session_state.book_content)
            estimated_pages = max(1, word_count // 250)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Words", word_count)
            with col2:
                st.metric("🔤 Characters", char_count)
            with col3:
                st.metric("📄 Est. Pages", estimated_pages)

# PAGE 4: GOOGLE DOCS LIVE
elif page == "🌐 Google Docs Live":
    st.title("🌐 Google Docs Live Integration")
    st.markdown("**Connect to Google Docs for real-time content synchronization!**")
    
    # Google Docs URL input
    st.markdown("### 🔗 Google Docs Connection")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        google_doc_url = st.text_input(
            "📄 Google Docs URL",
            value=st.session_state.google_doc_url,
            placeholder="https://docs.google.com/document/d/your-document-id/edit"
        )
        st.session_state.google_doc_url = google_doc_url
    
    with col2:
        if st.button("🔄 Fetch Content", use_container_width=True):
            if google_doc_url:
                with st.spinner("📥 Fetching content from Google Docs..."):
                    content = fetch_google_doc_content(google_doc_url)
                    if content:
                        st.session_state.live_content = content
                        st.session_state.book_content = content
                        st.success("✅ Content fetched successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to fetch content. Make sure the document is publicly accessible.")
            else:
                st.warning("⚠️ Please enter a Google Docs URL")
    
    # Auto-refresh settings
    st.markdown("### ⚙️ Auto-Refresh Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        auto_refresh = st.checkbox("🔄 Enable Auto-Refresh", value=False)
    
    with col2:
        refresh_interval = st.selectbox("⏱️ Refresh Interval", [30, 60, 120, 300], index=1, format_func=lambda x: f"{x} seconds")
    
    with col3:
        if st.button("🔄 Refresh Now", use_container_width=True):
            if st.session_state.google_doc_url:
                with st.spinner("🔄 Refreshing content..."):
                    content = fetch_google_doc_content(st.session_state.google_doc_url)
                    if content:
                        st.session_state.live_content = content
                        st.session_state.book_content = content
                        st.success("✅ Content refreshed!")
                        st.rerun()
    
    # Display live content
    if st.session_state.live_content:
        st.markdown("### 📄 Live Content")
        
        # Content statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            word_count = len(st.session_state.live_content.split())
            st.metric("📊 Words", word_count)
        
        with col2:
            char_count = len(st.session_state.live_content)
            st.metric("🔤 Characters", char_count)
        
        with col3:
            para_count = len([p for p in st.session_state.live_content.split('\n\n') if p.strip()])
            st.metric("📝 Paragraphs", para_count)
        
        with col4:
            estimated_pages = max(1, word_count // 250)
            st.metric("📄 Est. Pages", estimated_pages)
        
        # Content display
        st.text_area("📄 Document Content", st.session_state.live_content, height=400, key="live_content_display")
        
        # Action buttons
        st.markdown("### 🛠️ Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📝 Format Text", use_container_width=True):
                formatted_text = format_text_for_book(st.session_state.live_content, "novel")
                st.session_state.book_content = formatted_text
                st.success("✅ Text formatted!")
        
        with col2:
            if st.button("📄 Generate PDF", use_container_width=True):
                if st.session_state.book_metadata['title']:
                    with st.spinner("📄 Creating PDF..."):
                        try:
                            pdf_buffer = create_pdf(st.session_state.live_content, st.session_state.book_metadata, "novel")
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"{st.session_state.book_metadata['title']}.pdf",
                                mime="application/pdf"
                            )
                            st.success("✅ PDF generated!")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Please set book title in metadata")
        
        with col3:
            if st.button("📚 Generate EPUB", use_container_width=True):
                if st.session_state.book_metadata['title']:
                    with st.spinner("📚 Creating EPUB..."):
                        try:
                            epub_buffer = create_epub(st.session_state.live_content, st.session_state.book_metadata)
                            st.download_button(
                                label="⬇️ Download EPUB",
                                data=epub_buffer.getvalue(),
                                file_name=f"{st.session_state.book_metadata['title']}.epub",
                                mime="application/epub+zip"
                            )
                            st.success("✅ EPUB generated!")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Please set book title in metadata")
        
        with col4:
            if st.button("🚀 Send to Webhook", use_container_width=True):
                with st.spinner("📤 Sending to hardcoded webhook..."):
                    try:
                        payload = {
                            "timestamp": datetime.now().isoformat(),
                            "source": "google_docs_live",
                            "content": st.session_state.live_content,
                            "metadata": st.session_state.book_metadata,
                            "url": st.session_state.google_doc_url,
                            "app_version": "Book Buddy Complete Edition"
                        }
                        
                        response = requests.post(HARDCODED_WEBHOOK_URL, json=payload, timeout=30)
                        
                        if response.status_code == 200:
                            st.success("✅ Content sent to webhook!")
                        else:
                            st.error(f"❌ Webhook Error: {response.status_code}")
                    except Exception as e:
                        st.error(f"💥 Error: {str(e)}")
    
    else:
        st.info("📄 No content loaded. Please enter a Google Docs URL and fetch content.")
        
        # Instructions
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. **Share your Google Doc**: Make sure your Google Document is shared publicly or with "Anyone with the link can view"
        2. **Copy the URL**: Copy the full URL from your browser when viewing the document
        3. **Paste and Fetch**: Paste the URL above and click "Fetch Content"
        4. **Auto-Refresh**: Enable auto-refresh to keep content synchronized
        
        **Supported URL formats:**
        - `https://docs.google.com/document/d/DOCUMENT_ID/edit`
        - `https://docs.google.com/document/d/DOCUMENT_ID/edit#gid=0`
        """)

# PAGE 5: SETTINGS
elif page == "⚙️ Settings":
    st.title("⚙️ Settings & Configuration")
    st.markdown("**Configure your Book Buddy application settings**")
    
    # Hardcoded Webhook Info
    st.markdown("### 🎯 Primary Webhook (Hardcoded)")
    st.info(f"**Primary webhook URL:** `{HARDCODED_WEBHOOK_URL}`")
    st.markdown("This webhook is hardcoded and will always receive audio recordings automatically.")
    
    # Test hardcoded webhook
    if st.button("🧪 Test Hardcoded Webhook", use_container_width=True):
        with st.spinner("🧪 Testing hardcoded webhook connection..."):
            try:
                test_payload = {
                    "test": True,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Test connection from Book Buddy",
                    "app_version": "Book Buddy Complete Edition"
                }
                
                response = requests.post(HARDCODED_WEBHOOK_URL, json=test_payload, timeout=30)
                
                if response.status_code == 200:
                    st.success("✅ Hardcoded webhook connection successful!")
                    if response.text:
                        st.json(response.json())
                else:
                    st.error(f"❌ Hardcoded webhook returned status code: {response.status_code}")
            except Exception as e:
                st.error(f"💥 Hardcoded webhook test failed: {str(e)}")
    
    # Additional Webhook Configuration
    st.markdown("### 🔗 Additional Webhook Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        webhook_url_setting = st.text_input("🌐 Additional Webhook URL (Optional)", value=webhook_url, key="webhook_setting")
        webhook_timeout = st.number_input("⏱️ Webhook Timeout (seconds)", min_value=5, max_value=120, value=30)
    
    with col2:
        webhook_retries = st.number_input("🔄 Max Retries", min_value=0, max_value=5, value=3)
        if st.button("🧪 Test Additional Webhook", use_container_width=True):
            if webhook_url_setting:
                with st.spinner("🧪 Testing additional webhook connection..."):
                    try:
                        test_payload = {
                            "test": True,
                            "timestamp": datetime.now().isoformat(),
                            "message": "Test connection from Book Buddy (Additional Webhook)",
                            "app_version": "Book Buddy Complete Edition"
                        }
                        
                        response = requests.post(webhook_url_setting, json=test_payload, timeout=webhook_timeout)
                        
                        if response.status_code == 200:
                            st.success("✅ Additional webhook connection successful!")
                        else:
                            st.error(f"❌ Additional webhook returned status code: {response.status_code}")
                    except Exception as e:
                        st.error(f"💥 Additional webhook test failed: {str(e)}")
            else:
                st.warning("⚠️ Please enter an additional webhook URL")
    
    # Audio Settings
    st.markdown("### 🎙️ Audio Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        audio_quality = st.selectbox("🎵 Audio Quality", ["High", "Medium", "Low"], index=1)
        auto_send_audio = st.checkbox("🚀 Auto-send after recording", value=True, disabled=True, help="Always enabled for hardcoded webhook")
    
    with col2:
        max_recording_time = st.number_input("⏱️ Max Recording Time (minutes)", min_value=1, max_value=30, value=10)
        audio_format = st.selectbox("📁 Audio Format", ["webm", "mp3", "wav"], index=0)
    
    # Export Settings
    st.markdown("### 📄 Export Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_pdf_style = st.selectbox("📄 Default PDF Style", ["novel", "academic", "poetry", "screenplay"], index=0)
        include_metadata = st.checkbox("📋 Include Metadata in Exports", value=True)
    
    with col2:
        default_font_size = st.number_input("🔤 Default Font Size", min_value=8, max_value=24, value=12)
        page_margins = st.number_input("📏 Page Margins (inches)", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
    
    # Google Docs Settings
    st.markdown("### 🌐 Google Docs Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_refresh_interval = st.selectbox("⏱️ Default Refresh Interval", [30, 60, 120, 300], index=1, format_func=lambda x: f"{x} seconds")
        auto_format_on_fetch = st.checkbox("🎨 Auto-format on fetch", value=True)
    
    with col2:
        max_content_length = st.number_input("📏 Max Content Length (characters)", min_value=1000, max_value=1000000, value=100000)
        backup_content = st.checkbox("💾 Backup content locally", value=True)
    
    # Application Settings
    st.markdown("### 🔧 Application Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        theme_mode = st.selectbox("🎨 Theme Mode", ["Auto", "Light", "Dark"], index=0)
        show_advanced_options = st.checkbox("🔬 Show Advanced Options", value=False)
    
    with col2:
        debug_mode = st.checkbox("🐛 Debug Mode", value=False)
        analytics_enabled = st.checkbox("📊 Enable Analytics", value=True)
    
    # Data Management
    st.markdown("### 💾 Data Management")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗑️ Clear Messages", use_container_width=True):
            st.session_state.messages = []
            st.success("✅ Messages cleared!")
    
    with col2:
        if st.button("🧹 Clear Content", use_container_width=True):
            st.session_state.book_content = ""
            st.session_state.live_content = ""
            st.success("✅ Content cleared!")
    
    with col3:
        if st.button("📋 Reset Metadata", use_container_width=True):
            st.session_state.book_metadata = {
                'title': '',
                'author': '',
                'genre': '',
                'isbn': '',
                'publisher': '',
                'year': '',
                'description': ''
            }
            st.success("✅ Metadata reset!")
    
    with col4:
        if st.button("🔄 Reset All", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ['page_selector']:  # Keep page selector
                    del st.session_state[key]
            st.success("✅ All data reset!")
            st.rerun()
    
    # Export/Import Settings
    st.markdown("### 📦 Export/Import Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Export Settings", use_container_width=True):
            settings_data = {
                "hardcoded_webhook_url": HARDCODED_WEBHOOK_URL,
                "additional_webhook_url": webhook_url_setting,
                "webhook_timeout": webhook_timeout,
                "audio_quality": audio_quality,
                "auto_send_audio": auto_send_audio,
                "default_pdf_style": default_pdf_style,
                "default_font_size": default_font_size,
                "theme_mode": theme_mode,
                "debug_mode": debug_mode
            }
            
            settings_json = json.dumps(settings_data, indent=2)
            
            st.download_button(
                label="⬇️ Download Settings",
                data=settings_json,
                file_name="book_buddy_settings.json",
                mime="application/json",
                use_container_width=True
            )
    
    with col2:
        uploaded_settings = st.file_uploader("📥 Import Settings", type=['json'])
        if uploaded_settings is not None:
            try:
                settings_data = json.load(uploaded_settings)
                st.success("✅ Settings imported successfully!")
                st.json(settings_data)
            except Exception as e:
                st.error(f"❌ Error importing settings: {str(e)}")
    
    # System Information
    st.markdown("### ℹ️ System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **📱 Application Info:**
        - Version: 1.0.0
        - Build: Complete Edition
        - Last Updated: {datetime.now().strftime('%Y-%m-%d')}
        - Hardcoded Webhook: Active
        """)
    
    with col2:
        st.info(f"""
        **📊 Session Stats:**
        - Messages: {len(st.session_state.messages)}
        - Content Length: {len(st.session_state.book_content)} chars
        - Live Content: {len(st.session_state.live_content)} chars
        - Auto-send: Enabled
        """)
    
    # Advanced Settings (if enabled)
    if show_advanced_options:
        st.markdown("### 🔬 Advanced Settings")
        
        with st.expander("🔧 Advanced Configuration", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                custom_css = st.text_area("🎨 Custom CSS", height=100, placeholder="Enter custom CSS here...")
                api_rate_limit = st.number_input("⚡ API Rate Limit (requests/minute)", min_value=1, max_value=1000, value=60)
            
            with col2:
                cache_size = st.number_input("💾 Cache Size (MB)", min_value=10, max_value=1000, value=100)
                log_level = st.selectbox("📝 Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"], index=1)
            
            if st.button("💾 Save Advanced Settings", use_container_width=True):
                st.success("✅ Advanced settings saved!")

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>📚 <strong>Book Buddy - Complete Edition</strong> | Built with ❤️ using Streamlit</p>
    <p>🎙️ Voice Recording | 📝 Text Formatting | 📄 PDF/EPUB Generation | 🌐 Google Docs Integration</p>
    <p>🎯 <strong>Auto-send to:</strong> {HARDCODED_WEBHOOK_URL}</p>
</div>
""", unsafe_allow_html=True)
