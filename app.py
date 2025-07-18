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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import ebooklib
from ebooklib import epub
import tempfile
import os

# Configuration
DEFAULT_WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook-test/61e8b566-40c1-4925-940b-c6e74b9563cc"

# Page configuration
st.set_page_config(
    page_title="🎙️ Book Buddy - Enhanced Edition", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .section-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #e0e0e0;
    }
    
    .status-success {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .status-error {
        background: linear-gradient(135deg, #f44336, #d32f2f);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .status-info {
        background: linear-gradient(135deg, #2196F3, #1976D2);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    
    .action-button {
        background: linear-gradient(45deg, #FF6B6B, #FF8E8E);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 25px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
    }
    
    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'webhook_url': DEFAULT_WEBHOOK_URL,
        'recording_title': '',
        'recording_description': '',
        'user_name': 'Book Buddy User',
        'book_type': 'Fiction',
        'content': '',
        'metadata': {
            'title': '',
            'author': '',
            'genre': 'Fiction',
            'description': '',
            'tags': []
        },
        'webhook_responses': [],
        'last_recording': None,
        'audio_quality': 'High',
        'auto_send': True,
        'show_advanced': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Utility functions
def validate_webhook_url(url):
    """Validate webhook URL format"""
    try:
        import urllib.parse
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def send_to_webhook(payload, webhook_url=None):
    """Enhanced webhook sending with better error handling"""
    url = webhook_url or st.session_state.webhook_url
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Book-Buddy-Enhanced/1.1.0'
        }
        
        # Add timestamp if not present
        if 'timestamp' not in payload:
            payload['timestamp'] = datetime.now().isoformat()
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # Store response in session state
        response_data = {
            'timestamp': datetime.now().isoformat(),
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'payload_size': len(json.dumps(payload)),
            'response_text': response.text[:500] if response.text else None
        }
        
        st.session_state.webhook_responses.insert(0, response_data)
        # Keep only last 10 responses
        st.session_state.webhook_responses = st.session_state.webhook_responses[:10]
        
        if response.status_code == 200:
            return True, "Successfully sent to webhook!", response_data
        else:
            return False, f"Webhook returned status {response.status_code}", response_data
            
    except requests.exceptions.Timeout:
        error_data = {'error': 'Request timeout', 'timestamp': datetime.now().isoformat()}
        st.session_state.webhook_responses.insert(0, error_data)
        return False, "Request timed out (30s)", error_data
    except requests.exceptions.ConnectionError:
        error_data = {'error': 'Connection error', 'timestamp': datetime.now().isoformat()}
        st.session_state.webhook_responses.insert(0, error_data)
        return False, "Could not connect to webhook", error_data
    except Exception as e:
        error_data = {'error': str(e), 'timestamp': datetime.now().isoformat()}
        st.session_state.webhook_responses.insert(0, error_data)
        return False, f"Error: {str(e)}", error_data

def create_enhanced_voice_recorder():
    """Create enhanced voice recorder with better UI and functionality"""
    webhook_url = st.session_state.webhook_url
    title = st.session_state.recording_title
    description = st.session_state.recording_description
    user_name = st.session_state.user_name
    book_type = st.session_state.book_type
    auto_send = st.session_state.auto_send
    
    recorder_html = f"""
    <div id="voice-recorder-enhanced" style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        margin: 20px 0;
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0 0 10px 0; font-size: 28px; font-weight: 700;">🎙️ Enhanced Voice Recorder</h2>
            <p style="margin: 0; opacity: 0.9; font-size: 16px;">Professional audio recording with auto-webhook integration</p>
        </div>
        
        <!-- Webhook Status -->
        <div style="
            background: rgba(255,255,255,0.15);
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                <div>
                    <strong>🎯 Webhook:</strong> 
                    <span style="font-family: monospace; font-size: 12px; opacity: 0.8;">{webhook_url[:50]}...</span>
                </div>
                <div style="margin-top: 5px;">
                    <span style="background: rgba(76, 175, 80, 0.8); padding: 4px 12px; border-radius: 15px; font-size: 12px;">
                        ✅ Auto-send: {'ON' if auto_send else 'OFF'}
                    </span>
                </div>
            </div>
        </div>
        
        <!-- Recording Controls -->
        <div style="text-align: center; margin-bottom: 25px;">
            <button id="recordBtn" style="
                background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
                color: white;
                border: none;
                padding: 20px 40px;
                font-size: 18px;
                border-radius: 50px;
                cursor: pointer;
                margin: 0 10px;
                transition: all 0.3s ease;
                box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
                font-weight: bold;
                min-width: 180px;
            ">🎙️ Start Recording</button>
            
            <button id="stopBtn" disabled style="
                background: linear-gradient(45deg, #666, #888);
                color: white;
                border: none;
                padding: 20px 40px;
                font-size: 18px;
                border-radius: 50px;
                cursor: not-allowed;
                margin: 0 10px;
                transition: all 0.3s ease;
                font-weight: bold;
                min-width: 180px;
            ">⏹️ Stop Recording</button>
        </div>
        
        <!-- Status Display -->
        <div id="statusDisplay" style="
            text-align: center;
            font-size: 18px;
            font-weight: 600;
            margin: 20px 0;
            min-height: 30px;
        ">📚 Ready to record your thoughts</div>
        
        <!-- Waveform Visualization -->
        <div id="waveformContainer" style="
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 25px 0;
            display: none;
            position: relative;
            height: 100px;
            overflow: hidden;
        ">
            <div id="waveform" style="
                display: flex;
                align-items: end;
                justify-content: center;
                height: 100%;
                gap: 2px;
            "></div>
        </div>
        
        <!-- Recording Stats -->
        <div id="recordingStats" style="
            display: none;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 12px;
            margin: 20px 0;
        ">
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <div style="font-size: 24px; font-weight: bold;" id="duration">00:00</div>
                    <div style="font-size: 12px; opacity: 0.8;">Duration</div>
                </div>
                <div>
                    <div style="font-size: 24px; font-weight: bold;" id="fileSize">0 KB</div>
                    <div style="font-size: 12px; opacity: 0.8;">Size</div>
                </div>
                <div>
                    <div style="font-size: 24px; font-weight: bold;" id="quality">High</div>
                    <div style="font-size: 12px; opacity: 0.8;">Quality</div>
                </div>
            </div>
        </div>
        
        <!-- Audio Playback -->
        <div id="playbackContainer" style="display: none; margin: 25px 0;">
            <div style="margin-bottom: 15px; text-align: center;">
                <strong>🎵 Recording Playback</strong>
            </div>
            <audio id="audioPlayback" controls style="
                width: 100%;
                border-radius: 10px;
                background: rgba(255,255,255,0.1);
            "></audio>
        </div>
        
        <!-- Webhook Status -->
        <div id="webhookStatus" style="
            display: none;
            padding: 15px;
            border-radius: 12px;
            margin: 20px 0;
            text-align: center;
            font-weight: 600;
        "></div>
        
        <!-- Progress Bar -->
        <div id="progressContainer" style="display: none; margin: 20px 0;">
            <div style="background: rgba(255,255,255,0.2); border-radius: 10px; overflow: hidden;">
                <div id="progressBar" style="
                    background: linear-gradient(45deg, #4CAF50, #45a049);
                    height: 8px;
                    width: 0%;
                    transition: width 0.3s ease;
                "></div>
            </div>
            <div id="progressText" style="text-align: center; margin-top: 10px; font-size: 14px;"></div>
        </div>
        
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
    let stream;

    const recordBtn = document.getElementById("recordBtn");
    const stopBtn = document.getElementById("stopBtn");
    const statusDisplay = document.getElementById("statusDisplay");
    const playback = document.getElementById("audioPlayback");
    const base64output = document.getElementById("base64output");
    const waveformContainer = document.getElementById("waveformContainer");
    const waveform = document.getElementById("waveform");
    const recordingStats = document.getElementById("recordingStats");
    const playbackContainer = document.getElementById("playbackContainer");
    const webhookStatus = document.getElementById("webhookStatus");
    const progressContainer = document.getElementById("progressContainer");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    
    const durationSpan = document.getElementById("duration");
    const fileSizeSpan = document.getElementById("fileSize");
    const qualitySpan = document.getElementById("quality");

    function updateProgress(percent, text) {{
        progressContainer.style.display = 'block';
        progressBar.style.width = percent + '%';
        progressText.textContent = text;
        
        if (percent >= 100) {{
            setTimeout(() => {{
                progressContainer.style.display = 'none';
            }}, 2000);
        }}
    }}

    function showWebhookStatus(message, isSuccess = true) {{
        webhookStatus.style.display = 'block';
        webhookStatus.textContent = message;
        webhookStatus.style.background = isSuccess 
            ? 'rgba(76, 175, 80, 0.8)' 
            : 'rgba(244, 67, 54, 0.8)';
        
        setTimeout(() => {{
            webhookStatus.style.display = 'none';
        }}, 5000);
    }}

    function updateButtonStyles() {{
        if (isRecording) {{
            recordBtn.style.background = "linear-gradient(45deg, #666, #888)";
            recordBtn.style.cursor = "not-allowed";
            recordBtn.style.transform = "scale(0.95)";
            recordBtn.style.boxShadow = "0 4px 15px rgba(0,0,0,0.2)";
            
            stopBtn.style.background = "linear-gradient(45deg, #ff4757, #ff6b6b)";
            stopBtn.style.cursor = "pointer";
            stopBtn.style.boxShadow = "0 8px 25px rgba(255, 71, 87, 0.5)";
            stopBtn.style.transform = "scale(1.05)";
        }} else {{
            recordBtn.style.background = "linear-gradient(45deg, #ff6b6b, #ff8e8e)";
            recordBtn.style.cursor = "pointer";
            recordBtn.style.transform = "scale(1)";
            recordBtn.style.boxShadow = "0 8px 25px rgba(255, 107, 107, 0.4)";
            
            stopBtn.style.background = "linear-gradient(45deg, #666, #888)";
            stopBtn.style.cursor = "not-allowed";
            stopBtn.style.transform = "scale(0.95)";
            stopBtn.style.boxShadow = "0 4px 15px rgba(0,0,0,0.2)";
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
            statusDisplay.innerHTML = `🔴 Recording... ${{mins}}:${{secs.toString().padStart(2, '0')}}`;
        }}, 1000);
    }}

    function stopTimer() {{
        clearInterval(recordingTimer);
    }}

    function createWaveformBars() {{
        waveform.innerHTML = '';
        for(let i = 0; i < 30; i++) {{
            const bar = document.createElement('div');
            bar.style.cssText = `
                width: 4px;
                background: linear-gradient(to top, #ff6b6b, #ff8e8e, #ffffff);
                border-radius: 2px;
                transition: height 0.1s ease;
                height: 10px;
            `;
            waveform.appendChild(bar);
        }}
    }}

    function drawWaveform() {{
        if (!analyser || !isRecording) return;
        
        analyser.getByteFrequencyData(dataArray);
        const bars = waveform.children;
        
        for(let i = 0; i < bars.length; i++) {{
            const barHeight = (dataArray[i * 4] / 255) * 70 + 10;
            bars[i].style.height = barHeight + 'px';
        }}
        
        animationId = requestAnimationFrame(drawWaveform);
    }}

    async function sendAudioToWebhook(base64String) {{
        console.log('Preparing to send audio to webhook...');
        updateProgress(10, 'Preparing payload...');
        
        const payload = {{
            timestamp: new Date().toISOString(),
            title: "{title}" || "Voice Recording",
            description: "{description}" || "Audio recording from Book Buddy",
            user_name: "{user_name}",
            book_type: "{book_type}",
            audio_data: base64String,
            audio_format: 'audio/webm',
            recording_duration: seconds,
            file_size: Math.round(base64String.length * 0.75),
            metadata: {{
                quality: "High",
                auto_sent: true,
                app_version: "1.1.0",
                browser: navigator.userAgent.split(' ').slice(-2).join(' ')
            }},
            source: 'enhanced_voice_recording',
            app_name: 'Book Buddy Enhanced'
        }};

        updateProgress(30, 'Sending to webhook...');
        
        try {{
            console.log('Sending to webhook:', '{webhook_url}');
            
            const response = await fetch('{webhook_url}', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'User-Agent': 'Book-Buddy-Enhanced/1.1.0'
                }},
                body: JSON.stringify(payload)
            }});
            
            updateProgress(80, 'Processing response...');
            
            if (response.ok) {{
                const responseText = await response.text();
                console.log('Webhook success:', response.status);
                
                updateProgress(100, 'Successfully sent!');
                showWebhookStatus('✅ Audio sent successfully to n8n webhook!', true);
                
                // Store success info for Streamlit
                window.lastWebhookResponse = {{
                    success: true,
                    status: response.status,
                    response: responseText,
                    timestamp: new Date().toISOString(),
                    payload_size: JSON.stringify(payload).length
                }};
                
            }} else {{
                throw new Error(`HTTP ${{response.status}}: ${{await response.text()}}`);
            }}
        }} catch (error) {{
            console.error('Webhook error:', error);
            updateProgress(0, '');
            showWebhookStatus(`❌ Failed to send: ${{error.message}}`, false);
            
            // Store error info for Streamlit
            window.lastWebhookResponse = {{
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            }};
        }}
    }}

    recordBtn.onclick = async () => {{
        console.log('Starting recording...');
        try {{
            stream = await navigator.mediaDevices.getUserMedia({{ 
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
                fileSizeSpan.textContent = formatFileSize(e.data.size);
            }};
            
            mediaRecorder.onstop = async () => {{
                console.log('Recording stopped, processing...');
                const blob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                
                statusDisplay.innerHTML = "🔄 Processing audio...";
                
                const arrayBuffer = await blob.arrayBuffer();
                const base64String = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
                
                base64output.value = base64String;
                playback.src = URL.createObjectURL(blob);
                playbackContainer.style.display = 'block';
                
                statusDisplay.innerHTML = "✅ Recording complete!";
                waveformContainer.style.display = 'none';
                
                // Auto-send if enabled
                if ({str(auto_send).lower()}) {{
                    statusDisplay.innerHTML = "📤 Auto-sending to webhook...";
                    await sendAudioToWebhook(base64String);
                }} else {{
                    statusDisplay.innerHTML = "✅ Recording ready (auto-send disabled)";
                }}
                
                // Cleanup
                stream.getTracks().forEach(track => track.stop());
                if (audioContext) {{
                    audioContext.close();
                }}
            }};

            mediaRecorder.start(100);
            startTimer();
            waveformContainer.style.display = 'block';
            createWaveformBars();
            drawWaveform();
            
            recordBtn.disabled = true;
            stopBtn.disabled = false;
            updateButtonStyles();
            
        }} catch (err) {{
            console.error('Error accessing microphone:', err);
            statusDisplay.innerHTML = "❌ Error: " + err.message;
            showWebhookStatus("❌ Microphone access denied", false);
        }}
    }};

    stopBtn.onclick = () => {{
        console.log('Stopping recording...');
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

    function formatFileSize(bytes) {{
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }}

    // Initialize
    updateButtonStyles();
    console.log('Enhanced voice recorder initialized');
    console.log('Webhook URL:', '{webhook_url}');
    console.log('Auto-send enabled:', {str(auto_send).lower()});
    </script>

    <style>
    #voice-recorder-enhanced button:hover:not(:disabled) {{
        transform: scale(1.05) !important;
        transition: all 0.2s ease;
    }}
    
    #voice-recorder-enhanced button:active:not(:disabled) {{
        transform: scale(0.98) !important;
    }}
    
    @keyframes pulse {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
        100% {{ opacity: 1; }}
    }}
    
    #waveformContainer {{
        animation: pulse 2s infinite;
    }}
    
    #webhookStatus {{
        animation: slideIn 0.3s ease-out;
    }}
    
    @keyframes slideIn {{
        from {{ 
            opacity: 0; 
            transform: translateY(-10px); 
        }}
        to {{ 
            opacity: 1; 
            transform: translateY(0); 
        }}
    }}
    </style>
    """
    return recorder_html

def create_pdf(content, metadata):
    """Create PDF with enhanced formatting"""
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
    
    story = []
    
    # Title page
    if metadata.get('title'):
        story.append(Paragraph(metadata['title'], title_style))
    
    if metadata.get('author'):
        author_style = ParagraphStyle('Author', parent=styles['Normal'], 
                                    fontSize=14, alignment=TA_CENTER, spaceAfter=20)
        story.append(Paragraph(f"by {metadata['author']}", author_style))
    
    story.append(Spacer(1, 50))
    
    # Content
    if content:
        body_style = ParagraphStyle('Body', parent=styles['Normal'], 
                                  fontSize=12, alignment=TA_JUSTIFY, spaceAfter=12)
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), body_style))
                story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Main application
def main():
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">🎙️ Book Buddy - Enhanced Edition</h1>
        <p style="margin: 10px 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Professional voice recording with intelligent webhook integration
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Webhook Status Bar
    webhook_status = "🟢 Connected" if validate_webhook_url(st.session_state.webhook_url) else "🔴 Invalid URL"
    st.markdown(f"""
    <div class="status-info">
        <strong>🎯 Webhook Status:</strong> {webhook_status} | 
        <strong>URL:</strong> <code>{st.session_state.webhook_url[:60]}...</code> |
        <strong>Auto-send:</strong> {'✅ Enabled' if st.session_state.auto_send else '❌ Disabled'}
    </div>
    """, unsafe_allow_html=True)
    
    # Configuration Section
    with st.expander("⚙️ Configuration & Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Webhook Settings")
            new_webhook_url = st.text_input(
                "Webhook URL", 
                value=st.session_state.webhook_url,
                help="n8n webhook endpoint URL"
            )
            if new_webhook_url != st.session_state.webhook_url:
                st.session_state.webhook_url = new_webhook_url
                st.rerun()
            
            st.session_state.auto_send = st.checkbox(
                "🔄 Auto-send recordings", 
                value=st.session_state.auto_send,
                help="Automatically send recordings to webhook after stopping"
            )
            
            if st.button("🧪 Test Webhook Connection"):
                with st.spinner("Testing webhook..."):
                    test_payload = {
                        "test": True,
                        "message": "Test from Book Buddy Enhanced",
                        "timestamp": datetime.now().isoformat()
                    }
                    success, message, response_data = send_to_webhook(test_payload)
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
        
        with col2:
            st.subheader("🎙️ Recording Settings")
            st.session_state.user_name = st.text_input(
                "Your Name", 
                value=st.session_state.user_name
            )
            
            book_types = ["Fiction", "Non-Fiction", "Biography", "Mystery", "Romance", 
                         "Science Fiction", "Fantasy", "Thriller", "Self-Help", "Business"]
            st.session_state.book_type = st.selectbox(
                "Book Type", 
                book_types, 
                index=book_types.index(st.session_state.book_type) if st.session_state.book_type in book_types else 0
            )
            
            st.session_state.audio_quality = st.selectbox(
                "Audio Quality", 
                ["High", "Medium", "Low"], 
                index=["High", "Medium", "Low"].index(st.session_state.audio_quality)
            )
    
    # Recording Metadata Section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📝 Recording Details")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.recording_title = st.text_input(
            "📖 Recording Title", 
            value=st.session_state.recording_title,
            placeholder="Enter a title for your recording"
        )
    
    with col2:
        st.session_state.recording_description = st.text_area(
            "📄 Description", 
            value=st.session_state.recording_description,
            placeholder="Describe what this recording is about",
            height=100
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Enhanced Voice Recorder Section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    recorder_component = components.html(create_enhanced_voice_recorder(), height=600)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Manual Actions Section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🚀 Manual Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Send Text to Webhook", use_container_width=True):
            if st.session_state.recording_title or st.session_state.recording_description:
                with st.spinner("Sending text data..."):
                    payload = {
                        "title": st.session_state.recording_title,
                        "description": st.session_state.recording_description,
                        "user_name": st.session_state.user_name,
                        "book_type": st.session_state.book_type,
                        "source": "manual_text",
                        "content": st.session_state.content
                    }
                    success, message, response_data = send_to_webhook(payload)
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
            else:
                st.warning("⚠️ Please enter a title or description")
    
    with col2:
        uploaded_file = st.file_uploader("📁 Upload Audio", type=['mp3', 'wav', 'ogg', 'webm', 'm4a'])
        if uploaded_file and st.button("📤 Send File", use_container_width=True):
            with st.spinner("Processing and sending file..."):
                try:
                    audio_bytes = uploaded_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    
                    payload = {
                        "title": st.session_state.recording_title or uploaded_file.name,
                        "description": st.session_state.recording_description,
                        "user_name": st.session_state.user_name,
                        "book_type": st.session_state.book_type,
                        "audio_data": audio_base64,
                        "audio_format": uploaded_file.type,
                        "filename": uploaded_file.name,
                        "file_size": len(audio_bytes),
                        "source": "file_upload"
                    }
                    
                    success, message, response_data = send_to_webhook(payload)
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
                except Exception as e:
                    st.error(f"❌ Error processing file: {str(e)}")
    
    with col3:
        if st.button("📄 Generate PDF", use_container_width=True):
            if st.session_state.content or st.session_state.recording_description:
                with st.spinner("Generating PDF..."):
                    try:
                        content = st.session_state.content or st.session_state.recording_description
                        metadata = {
                            'title': st.session_state.recording_title or 'Book Buddy Recording',
                            'author': st.session_state.user_name
                        }
                        pdf_buffer = create_pdf(content, metadata)
                        
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{metadata['title']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("✅ PDF generated successfully!")
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
            else:
                st.warning("⚠️ Please add some content first")
    
    with col4:
        if st.button("🗑️ Clear All Data", use_container_width=True):
            # Reset session state
            for key in ['recording_title', 'recording_description', 'content', 'webhook_responses']:
                if key in st.session_state:
                    if key == 'webhook_responses':
                        st.session_state[key] = []
                    else:
                        st.session_state[key] = ''
            st.success("✅ All data cleared!")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Content Section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📝 Additional Content")
    st.session_state.content = st.text_area(
        "Content", 
        value=st.session_state.content,
        placeholder="Add any additional text content here...",
        height=200
    )
    
    if st.session_state.content:
        col1, col2, col3 = st.columns(3)
        with col1:
            word_count = len(st.session_state.content.split())
            st.metric("📊 Words", word_count)
        with col2:
            char_count = len(st.session_state.content)
            st.metric("🔤 Characters", char_count)
        with col3:
            estimated_pages = max(1, word_count // 250)
            st.metric("📄 Est. Pages", estimated_pages)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Webhook Response History
    if st.session_state.webhook_responses:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📊 Webhook Response History")
        
        for i, response in enumerate(st.session_state.webhook_responses[:5]):
            with st.expander(f"Response {i+1} - {response.get('timestamp', 'Unknown time')[:19]}", expanded=i==0):
                if response.get('success'):
                    st.success(f"✅ Status: {response.get('status_code', 'Unknown')}")
                    if 'payload_size' in response:
                        st.info(f"📦 Payload size: {format_file_size(response['payload_size'])}")
                    if response.get('response_text'):
                        st.code(response['response_text'][:200] + "..." if len(response['response_text']) > 200 else response['response_text'])
                else:
                    st.error(f"❌ Error: {response.get('error', 'Unknown error')}")
                    if 'status_code' in response:
                        st.error(f"Status Code: {response['status_code']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p><strong>🎙️ Book Buddy - Enhanced Edition v1.1.0</strong></p>
        <p>Professional voice recording • Intelligent webhook integration • Modern UI/UX</p>
        <p>Built with ❤️ using Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

