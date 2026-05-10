import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  Play, Video, History, LogOut, Loader2, 
  RefreshCw, CheckCircle2, AlertCircle, Film, ListMusic, ChevronDown, ChevronUp
} from 'lucide-react';

const PROCESSING_STEPS = [
  { id: 'connect', label: 'Connecting to YouTube' },
  { id: 'download', label: 'Downloading subtitles' },
  { id: 'transcript', label: 'Processing transcript' },
  { id: 'index', label: 'Building search index' },
  { id: 'complete', label: 'Ready to chat' },
];

export default function Sidebar({ 
  currentVideo, 
  setCurrentVideo, 
  onLoadSession,
  currentSessionId,
  chatHistory,
  setChatHistory 
}) {
  const { token, logout } = useAuth();
  const [videoId, setVideoId] = useState('');
  const [playlistUrl, setPlaylistUrl] = useState('');
  const [sessions, setSessions] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [error, setError] = useState(null);
  const [showPlaylist, setShowPlaylist] = useState(false);
  const [playlistVideos, setPlaylistVideos] = useState([]);
  const [playlistProcessing, setPlaylistProcessing] = useState(false);
  const [processedVideos, setProcessedVideos] = useState({});
  const [playlistProgress, setPlaylistProgress] = useState({ current: 0, total: 0, title: '' });

  useEffect(() => {
    if (token) loadSessions();
  }, [token]);

  const loadSessions = async () => {
    try {
      const data = await api.getSessions(token);
      if (Array.isArray(data)) setSessions(data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  };

  const extractVideoId = (input) => {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
      /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/,
    ];
    for (const pattern of patterns) {
      const match = input.match(pattern);
      if (match) return match[1];
    }
    return input.substring(0, 11);
  };

  const simulateProgress = (callback) => {
    setProcessingStep(0);
    const interval = setInterval(() => {
      setProcessingStep(prev => {
        if (prev < PROCESSING_STEPS.length - 2) {
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 1500);
    
    callback().finally(() => {
      clearInterval(interval);
    });
  };

  const handleProcessVideo = async () => {
    if (!videoId.trim()) return;

    const rawInput = videoId.trim();
    const videoToProcess = extractVideoId(rawInput);

    setProcessing(true);
    setError(null);
    setVideoId('');

    for (let i = 0; i < 4; i++) {
      setProcessingStep(i);
      await new Promise(r => setTimeout(r, 400 + Math.random() * 200));
    }

    try {
      const result = await api.processVideo(rawInput, token);
      setProcessingStep(4);

      setCurrentVideo(videoToProcess);
      setChatHistory([]);
      loadSessions();
    } catch (err) {
      console.error('Process error:', err);
      setError(err.message);
      setProcessingStep(0);
      setVideoId(rawInput);
    } finally {
      setProcessing(false);
    }
  };

  const handleReset = () => {
    setCurrentVideo(null);
    setVideoId('');
    setChatHistory([]);
    setError(null);
    setProcessingStep(0);
    onLoadSession(null);
  };

  const handleProcessPlaylist = async () => {
    if (!playlistUrl.trim()) return;

    setPlaylistProcessing(true);
    setError(null);
    setPlaylistVideos([]);
    setPlaylistProgress({ current: 0, total: 0, title: '' });

    const videosMap = {};

    try {
      await api.processPlaylistStream(playlistUrl, token, (data) => {
        if (data.type === 'progress') {
          setPlaylistProgress({
            current: data.current,
            total: data.total,
            title: data.title
          });
        } else if (data.type === 'video_done') {
          videosMap[data.video.video_id] = data.video;
          setPlaylistVideos(Object.values(videosMap));
        } else if (data.type === 'complete') {
          setPlaylistVideos(data.videos);
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setPlaylistProcessing(false);
      setPlaylistProgress({ current: 0, total: 0, title: '' });
    }
  };

  const handleSelectVideo = (video) => {
    setCurrentVideo(video.video_id);
    setChatHistory([]);
    onLoadSession(null);
  };

  return (
    <aside className="w-80 bg-dark-800 border-r border-dark-700 flex flex-col h-screen">
      <div className="p-6 border-b border-dark-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center">
            <Play className="w-5 h-5 text-white fill-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">YTChatBot</h1>
            <p className="text-xs text-slate-500">AI Video Assistant</p>
          </div>
        </div>
      </div>

      <div className="p-4 border-b border-dark-700">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Video className="w-4 h-4" />
          Load Video
        </h2>
        
        <input
          type="text"
          value={videoId}
          onChange={(e) => setVideoId(e.target.value)}
          placeholder="Enter YouTube Video ID"
          className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
        />
        
        <div className="flex gap-2 mt-3">
          <button
            onClick={handleProcessVideo}
            disabled={!videoId.trim() || processing}
            className="flex-1 py-2.5 bg-gradient-to-r from-primary to-secondary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {processing ? (
              <Loader2 className="animate-spin h-4 w-4" />
            ) : (
              <Video className="w-4 h-4" />
            )}
            Load
          </button>
          <button
            onClick={handleReset}
            className="px-4 py-2.5 bg-dark-700 text-slate-300 text-sm font-medium rounded-xl hover:bg-dark-600 transition-all border border-dark-600 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {processing && (
          <div className="mt-4 p-4 bg-dark-700/50 rounded-xl border border-dark-600">
            <div className="flex items-center gap-2 mb-3">
              <Film className="w-5 h-5 text-red-500" />
              <span className="text-sm text-white font-medium">Processing Video</span>
            </div>
            <div className="space-y-2">
              {PROCESSING_STEPS.map((step, idx) => (
                <div key={step.id} className="flex items-center gap-3">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                    idx < processingStep 
                      ? 'bg-emerald-500 text-white' 
                      : idx === processingStep 
                        ? 'bg-primary text-white animate-pulse' 
                        : 'bg-dark-600 text-slate-500'
                  }`}>
                    {idx < processingStep ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : idx === processingStep ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      (idx + 1)
                    )}
                  </div>
                  <span className={`text-xs ${
                    idx <= processingStep ? 'text-slate-300' : 'text-slate-600'
                  }`}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-500/10 rounded-xl border border-red-500/30">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
              <div>
                <p className="text-sm text-red-400 font-medium">Error</p>
                <p className="text-xs text-red-300/80 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-b border-dark-700">
        <button
          onClick={() => setShowPlaylist(!showPlaylist)}
          className="w-full flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 hover:text-slate-300 transition-colors"
        >
          <span className="flex items-center gap-2">
            <ListMusic className="w-4 h-4" />
            Load Playlist
          </span>
          {showPlaylist ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showPlaylist && (
          <div className="space-y-3">
            <input
              type="text"
              value={playlistUrl}
              onChange={(e) => setPlaylistUrl(e.target.value)}
              placeholder="Paste YouTube playlist URL"
              className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
            />
            <button
              onClick={handleProcessPlaylist}
              disabled={!playlistUrl.trim() || playlistProcessing}
              className="w-full py-2.5 bg-gradient-to-r from-primary to-secondary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {playlistProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing {playlistProgress.current}/{playlistProgress.total}...
                </>
              ) : (
                <>
                  <ListMusic className="w-4 h-4" />
                  Load & Process Playlist
                </>
              )}
            </button>

            {playlistProcessing && playlistProgress.total > 0 && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                  <span>Processing: {playlistProgress.title.substring(0, 30)}...</span>
                  <span>{playlistProgress.current}/{playlistProgress.total}</span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-primary to-secondary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(playlistProgress.current / playlistProgress.total) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {playlistVideos.length > 0 && (
              <div className="mt-4 max-h-64 overflow-y-auto space-y-2">
                <p className="text-xs text-slate-400 mb-2">{playlistVideos.length} videos found</p>
                {playlistVideos.map((video) => (
                  <button
                    key={video.video_id}
                    onClick={() => handleSelectVideo(video)}
                    className={`w-full text-left p-3 rounded-xl transition-all border flex items-start gap-3 ${
                      currentVideo === video.video_id
                        ? 'bg-primary/10 border-primary/30'
                        : 'bg-dark-700 border-dark-600 hover:border-primary/30'
                    }`}
                  >
                    <img
                      src={`https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`}
                      alt={video.title}
                      className="w-16 h-12 rounded object-cover flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{video.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {video.status === 'processed' || video.status === 'already_loaded' ? (
                          <span className="text-xs text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" />
                            Ready
                          </span>
                        ) : video.status.startsWith('error') ? (
                          <span className="text-xs text-red-400 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Failed
                          </span>
                        ) : (
                          <span className="text-xs text-slate-500">Pending</span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {currentVideo && (
        <div className="p-4 border-b border-dark-700">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Video className="w-4 h-4" />
            Video Preview
          </h2>
          <div className="rounded-xl overflow-hidden border border-dark-600">
            <img
              src={`https://img.youtube.com/vi/${currentVideo}/hqdefault.jpg`}
              alt="Video thumbnail"
              className="w-full aspect-video object-cover"
            />
          </div>
          <div className="mt-3 px-3 py-2 bg-dark-700 rounded-lg flex items-center gap-2">
            <span className="text-xs text-slate-400">ID:</span>
            <code className="text-xs text-primary">{currentVideo}</code>
          </div>
          <div className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-medium border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Ready
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <History className="w-4 h-4" />
          Chat History
        </h2>
        
        {sessions.length > 0 ? (
          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onLoadSession(session)}
                className={`w-full text-left p-3 rounded-xl transition-all border ${
                  currentSessionId === session.id
                    ? 'bg-primary/10 border-primary/30'
                    : 'bg-dark-700 border-dark-600 hover:border-primary/30'
                }`}
              >
                <p className="text-sm font-medium text-white truncate">{session.title}</p>
                <p className="text-xs text-slate-500 mt-1">{session.message_count} messages</p>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500 text-center py-8">No past sessions yet</p>
        )}
      </div>

      <div className="p-4 border-t border-dark-700">
        <button
          onClick={logout}
          className="w-full py-2.5 bg-dark-700 text-slate-300 text-sm font-medium rounded-xl hover:bg-dark-600 transition-all flex items-center justify-center gap-2 border border-dark-600"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
