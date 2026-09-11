import { useEffect, useRef, forwardRef, useImperativeHandle, useState, useCallback } from 'react';
import { Film, Minimize2 } from 'lucide-react';

const MIN_W = 240;
const MAX_W = 560;

const YouTubePlayer = forwardRef(({ videoId, isVizOpen, vizWidth = 500 }, ref) => {
  const playerRef = useRef(null);
  const iframeRef = useRef(null);
  const [visible, setVisible] = useState(false);
  const lastSeekRef = useRef(null);
  const [playerWidth, setPlayerWidth] = useState(320);
  const resizing = useRef(false);
  const resizeStartX = useRef(0);
  const resizeStartW = useRef(0);
  const currentVideoRef = useRef(null);

  useEffect(() => {
    if (!videoId) { setVisible(false); return; }
    setVisible(true);
  }, [videoId]);

  useEffect(() => {
    if (!visible || !videoId || !iframeRef.current) return;

    currentVideoRef.current = videoId;

    if (!window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScript = document.getElementsByTagName('script')[0];
      firstScript.parentNode.insertBefore(tag, firstScript);
    }

    const onReady = () => {
      const vid = currentVideoRef.current;
      if (vid) playerRef.current?.loadVideoById?.(vid);
      if (lastSeekRef.current !== null && playerRef.current?.seekTo) {
        playerRef.current.seekTo(lastSeekRef.current, true);
        if (playerRef.current.playVideo) playerRef.current.playVideo();
        lastSeekRef.current = null;
      }
    };

    const initPlayer = () => {
      try {
        if (playerRef.current) playerRef.current.destroy();
        playerRef.current = new window.YT.Player(iframeRef.current, {
          events: { onReady },
        });
      } catch {}
    };

    if (window.YT?.Player) {
      initPlayer();
    } else {
      window.onYouTubeIframeAPIReady = initPlayer;
    }

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [visible]);

  useEffect(() => {
    if (!videoId || !playerRef.current?.loadVideoById) return;
    if (currentVideoRef.current === videoId) return;
    currentVideoRef.current = videoId;
    setVisible(true);
    playerRef.current.loadVideoById(videoId);
  }, [videoId]);

  const seekTo = useCallback((seconds) => {
    setVisible(true);
    if (playerRef.current?.seekTo) {
      playerRef.current.seekTo(seconds, true);
      if (playerRef.current.playVideo) playerRef.current.playVideo();
    } else {
      lastSeekRef.current = seconds;
    }
  }, []);

  useImperativeHandle(ref, () => ({ seekTo }));

  const [position, setPosition] = useState(null);
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const dragStartPos = useRef({ left: 0, top: 0 });

  const handleResizeDown = useCallback((e) => {
    resizing.current = true;
    resizeStartX.current = e.clientX;
    resizeStartW.current = playerWidth;
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  }, [playerWidth]);

  const handleDragDown = useCallback((e) => {
    if (e.button !== 0 || e.target.closest('button')) return;
    dragging.current = true;
    
    const el = e.currentTarget.closest('.fixed');
    const rect = el.getBoundingClientRect();
    const currentLeft = position?.left ?? rect.left;
    const currentTop = position?.top ?? rect.top;
    
    dragStart.current = { x: e.clientX, y: e.clientY };
    dragStartPos.current = { left: currentLeft, top: currentTop };
    
    document.body.style.cursor = 'move';
    document.body.style.userSelect = 'none';
  }, [position]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (resizing.current) {
        const delta = e.clientX - resizeStartX.current;
        setPlayerWidth(Math.max(MIN_W, Math.min(MAX_W, resizeStartW.current + delta)));
      } else if (dragging.current) {
        const deltaX = e.clientX - dragStart.current.x;
        const deltaY = e.clientY - dragStart.current.y;
        const playerHeight = playerWidth * 9/16 + 40;
        
        const newLeft = Math.max(0, Math.min(window.innerWidth - playerWidth, dragStartPos.current.left + deltaX));
        const newTop = Math.max(0, Math.min(window.innerHeight - playerHeight, dragStartPos.current.top + deltaY));
        
        setPosition({ left: newLeft, top: newTop });
      }
    };
    
    const handleMouseUp = () => {
      if (resizing.current) {
        resizing.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
      if (dragging.current) {
        dragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [playerWidth]);

  useEffect(() => {
    const handleWindowResize = () => {
      if (position) {
        const playerHeight = playerWidth * 9/16 + 40;
        const newLeft = Math.max(0, Math.min(window.innerWidth - playerWidth, position.left));
        const newTop = Math.max(0, Math.min(window.innerHeight - playerHeight, position.top));
        setPosition({ left: newLeft, top: newTop });
      }
    };
    window.addEventListener('resize', handleWindowResize);
    return () => window.removeEventListener('resize', handleWindowResize);
  }, [position, playerWidth]);

  if (!videoId) return null;

  return (
    <div
      className={`fixed z-50 rounded-xl overflow-hidden shadow-2xl border border-dark-600 bg-dark-900 ${
        (resizing.current || dragging.current) ? '' : 'transition-all duration-300'
      } ${visible ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
      style={{ 
        width: playerWidth,
        left: position ? `${position.left}px` : undefined,
        top: position ? `${position.top}px` : undefined,
        bottom: position ? 'auto' : '16px',
        right: position ? 'auto' : (isVizOpen ? vizWidth + 20 : 16)
      }}
    >
      <div 
        onMouseDown={handleDragDown}
        className="flex items-center justify-between px-3 py-2 bg-dark-800 cursor-move select-none"
      >
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Film className="w-3.5 h-3.5" />
          <span>Now Playing</span>
        </div>
        <button onClick={() => setVisible(false)} className="p-1 hover:text-white transition-colors">
          <Minimize2 className="w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>
      <div className="aspect-video relative">
        <iframe
          ref={iframeRef}
          id="yt-player"
          src={`https://www.youtube.com/embed/?enablejsapi=1&origin=${window.location.origin}`}
          className="w-full h-full"
          allow="autoplay; encrypted-media"
          allowFullScreen
        />
      </div>
      <div
        onMouseDown={handleResizeDown}
        className="absolute bottom-0 right-0 w-4 h-4 cursor-ew-resize hover:bg-primary/20 rounded-bl"
      >
        <div className="absolute bottom-1 right-1 w-2 h-2 border-r-2 border-b-2 border-slate-500 rounded-sm" />
      </div>
    </div>
  );
});

YouTubePlayer.displayName = 'YouTubePlayer';
export default YouTubePlayer;
