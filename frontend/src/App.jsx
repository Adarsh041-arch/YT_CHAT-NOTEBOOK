import { useState, useEffect, useRef } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { api } from './services/api';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import YouTubePlayer from './components/YouTubePlayer';

function AppContent() {
  const { token, loading } = useAuth();
  const [currentVideo, setCurrentVideo] = useState(null);
  const [currentVideoTitle, setCurrentVideoTitle] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [sessionName, setSessionName] = useState('');
  const [playlistInfo, setPlaylistInfo] = useState(null);
  const [isVizOpen, setIsVizOpen] = useState(false);
  const [vizWidth, setVizWidth] = useState(500);
  const playerRef = useRef(null);

  const fetchVideoInfo = async (videoId) => {
    if (!videoId) { setCurrentVideoTitle(''); return; }
    try {
      const resp = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
      if (resp.ok) {
        const data = await resp.json();
        setCurrentVideoTitle(data.title || videoId);
      } else {
        setCurrentVideoTitle(videoId);
      }
    } catch {
      setCurrentVideoTitle(videoId);
    }
  };

  const fetchPlaylistInfo = async (videoId) => {
    if (!videoId || !token) {
      setPlaylistInfo(null);
      return;
    }
    try {
      const data = await api.getPlaylistForVideo(videoId, token);
      setPlaylistInfo(data?.playlist_id ? data : null);
    } catch {
      setPlaylistInfo(null);
    }
  };

  useEffect(() => {
    fetchVideoInfo(currentVideo);
    fetchPlaylistInfo(currentVideo);
  }, [currentVideo, token]);

  const handleLoadSession = async (session) => {
    if (!session) {
      setSessionId(null);
      setChatHistory([]);
      setPlaylistInfo(null);
      setSessionName('');
      return;
    }

    try {
      const messages = await api.getSessionMessages(session.id, token);
      if (Array.isArray(messages)) {
        const history = [];
        let currentQ = '';
        for (const msg of messages) {
          if (msg.role === 'user') {
            currentQ = msg.content;
          } else {
            history.push({ role: 'user', content: currentQ });
            history.push({ role: 'assistant', content: msg.content });
          }
        }
        setChatHistory(history);
        setSessionId(session.id);
        setCurrentVideo(session.video_id);
        setSessionName(session.title || '');
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (!token) {
    return <Login />;
  }

  return (
    <div className="flex h-screen bg-dark-900">
      <Sidebar
        currentVideo={currentVideo}
        setCurrentVideo={setCurrentVideo}
        onLoadSession={handleLoadSession}
        currentSessionId={sessionId}
        chatHistory={chatHistory}
        setChatHistory={setChatHistory}
        playlistInfo={playlistInfo}
        setPlaylistInfo={setPlaylistInfo}
      />
      <div className="flex-1 flex flex-col">
        <YouTubePlayer ref={playerRef} videoId={currentVideo} isVizOpen={isVizOpen} vizWidth={vizWidth} />
        <Chat
          currentVideo={currentVideo}
          currentVideoTitle={currentVideoTitle}
          chatHistory={chatHistory}
          setChatHistory={setChatHistory}
          sessionId={sessionId}
          setSessionId={setSessionId}
          sessionName={sessionName}
          setSessionName={setSessionName}
          playlistInfo={playlistInfo}
          playerRef={playerRef}
          onVizOpenChange={setIsVizOpen}
          vizWidth={vizWidth}
          setVizWidth={setVizWidth}
        />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
