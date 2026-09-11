import { useState, useEffect, useRef, useCallback } from 'react';
import { SkeletonSessionCard, SkeletonVideoCard } from './Skeleton';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  Play, Video, History, LogOut, Loader2, 
  RefreshCw, CheckCircle2, AlertCircle, Film, ListMusic, ChevronDown, ChevronUp, GripVertical
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
  setChatHistory,
  playlistInfo,
  setPlaylistInfo
}) {
  const { token, logout } = useAuth();
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const handleMouseDown = useCallback((e) => {
    dragging.current = true;
    startX.current = e.clientX;
    startWidth.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [sidebarWidth]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      setSidebarWidth(Math.max(240, Math.min(480, startWidth.current + delta)));
    };
    const handleMouseUp = () => {
      if (dragging.current) {
        dragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => { window.removeEventListener('mousemove', handleMouseMove); window.removeEventListener('mouseup', handleMouseUp); };
  }, []);

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
  const [collapsedSections, setCollapsedSections] = useState({ video: false, playlist: false });

  useEffect(() => {
    if (token) loadSessions();
  }, [token]);

  const [sessionsLoading, setSessionsLoading] = useState(true);

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await api.getSessions(token);
      if (Array.isArray(data)) setSessions(data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
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

  const [retrying, setRetrying] = useState(false);

  const handleRetryPlaylist = async () => {
    if (!playlistUrl.trim()) return;
    setRetrying(true);
    setError(null);

    try {
      await api.retryPlaylistStream(playlistUrl, token, (data) => {
        if (data.type === 'progress') {
          setPlaylistProgress({
            current: data.current,
            total: data.total,
            title: data.title
          });
        } else if (data.type === 'video_done') {
          setPlaylistVideos(prev => {
            const updated = [...prev];
            const idx = updated.findIndex(v => v.video_id === data.video.video_id);
            if (idx >= 0) updated[idx] = data.video;
            else updated.push(data.video);
            return updated;
          });
        } else if (data.type === 'complete') {
          if (data.videos) {
            setPlaylistVideos(prev => {
              const updated = [...prev];
              for (const v of data.videos) {
                const idx = updated.findIndex(x => x.video_id === v.video_id);
                if (idx >= 0) updated[idx] = v;
                else updated.push(v);
              }
              return updated;
            });
          }
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setRetrying(false);
      setPlaylistProgress({ current: 0, total: 0, title: '' });
    }
  };

  const handleSelectVideo = (video) => {
    setCurrentVideo(video.video_id);
    setChatHistory([]);
    onLoadSession(null);
  };

  const sectionHeader = (label, icon, sectionKey) => (
    <button
      onClick={() => setCollapsedSections(prev => ({ ...prev, [sectionKey]: !prev[sectionKey] }))}
      className="w-full flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 hover:text-slate-300 transition-colors"
    >
      <span className="flex items-center gap-2">{icon}{label}</span>
      {collapsedSections[sectionKey] ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
    </button>
  );

  return (
    <aside style={{ width: sidebarWidth }} className="relative bg-dark-800 border-r border-dark-700 flex flex-col h-screen flex-shrink-0 transition-[width] duration-75">
      {/* Drag handle */}
      <div
        onMouseDown={handleMouseDown}
        className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-primary/30 active:bg-primary/50 z-10 transition-colors"
      >
        <div className="absolute right-0 top-1/2 -translate-y-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100">
          <GripVertical className="w-3 h-3 text-slate-500" />
        </div>
      </div>

      {/* Header */}
      <div className="p-5 border-b border-dark-700">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center flex-shrink-0">
            <Play className="w-4 h-4 text-white fill-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-bold text-white truncate">YTChatBot</h1>
            <p className="text-[10px] text-slate-500">AI Video Assistant</p>
          </div>
        </div>
      </div>

      {/* Section: Load Video */}
      <div className={`border-b border-dark-700/60 ${playlistInfo ? '' : ''}`}>
        <div className="p-4 pb-0">
          {sectionHeader(<Video className="w-3.5 h-3.5" />, 'Load Video', 'video')}
        </div>
        {!collapsedSections.video && (
          <div className="px-4 pb-4 space-y-3 animate-fadeIn">
            <input
              type="text"
              value={videoId}
              onChange={(e) => setVideoId(e.target.value)}
              placeholder="Enter YouTube Video ID"
              className="w-full px-3.5 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={handleProcessVideo}
                disabled={!videoId.trim() || processing}
                className="flex-1 py-2 bg-gradient-to-r from-primary to-secondary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
              >
                {processing ? <Loader2 className="animate-spin h-3.5 w-3.5" /> : <Video className="w-3.5 h-3.5" />}
                Load
              </button>
              <button
                onClick={handleReset}
                className="px-3.5 py-2 bg-dark-700 text-slate-300 text-sm font-medium rounded-xl hover:bg-dark-600 transition-all border border-dark-600 flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            {processing && (
              <div className="p-3.5 bg-dark-700/50 rounded-xl border border-dark-600">
                <div className="flex items-center gap-2 mb-2.5">
                  <Film className="w-4 h-4 text-red-500" />
                  <span className="text-xs text-white font-medium">Processing Video</span>
                </div>
                <div className="space-y-1.5">
                  {PROCESSING_STEPS.map((step, idx) => (
                    <div key={step.id} className="flex items-center gap-2.5">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${
                        idx < processingStep ? 'bg-emerald-500 text-white' : idx === processingStep ? 'bg-primary text-white animate-pulse' : 'bg-dark-600 text-slate-500'
                      }`}>
                        {idx < processingStep ? <CheckCircle2 className="w-2.5 h-2.5" /> : idx === processingStep ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <span className="text-[10px]">{idx + 1}</span>}
                      </div>
                      <span className={`text-[11px] ${idx <= processingStep ? 'text-slate-300' : 'text-slate-600'}`}>{step.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-500/10 rounded-xl border border-red-500/30">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-red-400 font-medium">Error</p>
                    <p className="text-[11px] text-red-300/80 mt-0.5 truncate">{error}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section: Load Playlist */}
      <div className={`border-b border-dark-700/60`}>
        <div className="p-4 pb-0">
          {sectionHeader(<ListMusic className="w-3.5 h-3.5" />, 'Load Playlist', 'playlist')}
        </div>
        {!collapsedSections.playlist && (
          <div className="px-4 pb-4 space-y-3 animate-fadeIn">
            <input
              type="text"
              value={playlistUrl}
              onChange={(e) => setPlaylistUrl(e.target.value)}
              placeholder="Paste YouTube playlist URL"
              className="w-full px-3.5 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
            />
            <button
              onClick={handleProcessPlaylist}
              disabled={!playlistUrl.trim() || playlistProcessing}
              className="w-full py-2 bg-gradient-to-r from-primary to-secondary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
            >
              {playlistProcessing ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" />Processing {playlistProgress.current}/{playlistProgress.total}...</>
              ) : (
                <><ListMusic className="w-3.5 h-3.5" />Load & Process Playlist</>
              )}
            </button>

            {playlistProcessing && playlistProgress.total > 0 && (
              <div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span className="truncate">{playlistProgress.title.substring(0, 25)}...</span>
                  <span className="flex-shrink-0">{playlistProgress.current}/{playlistProgress.total}</span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-1.5">
                  <div className="bg-gradient-to-r from-primary to-secondary h-1.5 rounded-full transition-all duration-300" style={{ width: `${(playlistProgress.current / playlistProgress.total) * 100}%` }} />
                </div>
              </div>
            )}

            {playlistProcessing && playlistVideos.length === 0 && (
              <div className="space-y-1.5">
                {[1,2,3].map(i => <div key={i} className="bg-dark-700/50 rounded-xl border border-dark-600/50"><SkeletonVideoCard /></div>)}
              </div>
            )}

            {playlistVideos.length > 0 && !playlistInfo && (
              <div className="max-h-48 overflow-y-auto space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] text-slate-400">{playlistVideos.length} videos</p>
                  {playlistVideos.some(v => v.status?.startsWith('error')) && (
                    <button onClick={handleRetryPlaylist} disabled={retrying} className="text-[11px] text-primary hover:text-primary/80 disabled:opacity-50 flex items-center gap-1">
                      {retrying ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <RefreshCw className="w-2.5 h-2.5" />}
                      Retry
                    </button>
                  )}
                </div>
                {playlistVideos.map(video => (
                  <button key={video.video_id} onClick={() => handleSelectVideo(video)}
                    className={`w-full text-left p-2.5 rounded-xl transition-all border flex items-start gap-2.5 ${
                      currentVideo === video.video_id ? 'bg-primary/10 border-primary/30' : 'bg-dark-700 border-dark-600 hover:border-primary/30'
                    }`}>
                    <img src={`https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`} alt="" className="w-14 h-10 rounded object-cover flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-white truncate">{video.title}</p>
                      <span className={`text-[10px] mt-0.5 inline-flex items-center gap-1 ${
                        video.status === 'processed' || video.status === 'already_loaded' ? 'text-emerald-400' : video.status?.startsWith('error') ? 'text-red-400' : 'text-slate-500'
                      }`}>
                        {video.status === 'processed' || video.status === 'already_loaded' ? <><CheckCircle2 className="w-2.5 h-2.5" />Ready</> : video.status?.startsWith('error') ? <><AlertCircle className="w-2.5 h-2.5" />Failed</> : 'Pending'}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Gradient separator before dynamic sections */}
      <div className="h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent mx-4" />

      {/* Section: Playlist Videos (stored) */}
      {playlistInfo && playlistInfo.videos.length > 0 && (
        <div className="border-b border-dark-700/60">
          <div className="p-4 pb-2">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <ListMusic className="w-3.5 h-3.5" />
              Playlist Videos
              <span className="text-[10px] text-slate-500 font-normal">({playlistInfo.videos.length})</span>
            </h2>
          </div>
          <div className="px-4 pb-3 max-h-48 overflow-y-auto space-y-1.5">
            {playlistInfo.videos.map(video => (
              <button key={video.video_id} onClick={() => { setCurrentVideo(video.video_id); setChatHistory([]); onLoadSession(null); }}
                className={`w-full text-left p-2.5 rounded-xl transition-all border flex items-start gap-2.5 ${
                  currentVideo === video.video_id ? 'bg-primary/10 border-primary/30' : 'bg-dark-700 border-dark-600 hover:border-primary/30'
                }`}>
                <img src={`https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`} alt="" className="w-14 h-10 rounded object-cover flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-white truncate">{video.title}</p>
                  <span className={`text-[10px] mt-0.5 inline-flex items-center gap-1 ${video.status === 'processed' ? 'text-emerald-400' : 'text-slate-500'}`}>
                    {video.status === 'processed' ? <><CheckCircle2 className="w-2.5 h-2.5" />Ready</> : 'Pending'}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Section: Chat History */}
      <div className="flex-1 overflow-y-auto p-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <History className="w-3.5 h-3.5" />
          Chat History
        </h2>
        {sessionsLoading ? (
          <div className="space-y-1">
            {[1,2,3].map(i => <div key={i} className="bg-dark-700/50 rounded-xl border border-dark-600/50"><SkeletonSessionCard /></div>)}
          </div>
        ) : sessions.length > 0 ? (
          <div className="space-y-1.5">
            {sessions.map(session => (
              <button key={session.id} onClick={() => onLoadSession(session)}
                className={`w-full text-left p-2.5 rounded-xl transition-all border ${
                  currentSessionId === session.id ? 'bg-primary/10 border-primary/30' : 'bg-dark-700 border-dark-600 hover:border-primary/30'
                }`}>
                <p className="text-xs font-medium text-white truncate">{session.title}</p>
                <p className="text-[10px] text-slate-500 mt-0.5">{session.message_count} messages</p>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 text-center py-6">No past sessions yet</p>
        )}
      </div>

      {/* Logout */}
      <div className="p-4 border-t border-dark-700">
        <button onClick={logout}
          className="w-full py-2 bg-dark-700 text-slate-300 text-xs font-medium rounded-xl hover:bg-dark-600 transition-all flex items-center justify-center gap-2 border border-dark-600">
          <LogOut className="w-3.5 h-3.5" />
          Logout
        </button>
      </div>
    </aside>
  );
}
