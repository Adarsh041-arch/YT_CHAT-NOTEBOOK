export function SkeletonLine({ className = '' }) {
  return <div className={`h-3 bg-dark-600/50 rounded animate-pulse ${className}`} />;
}

export function SkeletonBlock({ className = '' }) {
  return <div className={`bg-dark-600/50 rounded-xl animate-pulse ${className}`} />;
}

export function SkeletonVideoCard() {
  return (
    <div className="flex items-start gap-2.5 p-2.5">
      <SkeletonBlock className="w-14 h-10 flex-shrink-0" />
      <div className="flex-1 space-y-1.5 min-w-0">
        <SkeletonLine className="w-3/4" />
        <SkeletonLine className="w-1/4" />
      </div>
    </div>
  );
}

export function SkeletonSessionCard() {
  return (
    <div className="p-2.5 space-y-1.5">
      <SkeletonLine className="w-2/3" />
      <SkeletonLine className="w-1/5" />
    </div>
  );
}

export function SkeletonChatBubble() {
  return (
    <div className="flex justify-start">
      <div className="max-w-[70%] rounded-2xl px-5 py-3 bg-dark-800 border border-dark-700 rounded-bl-md space-y-2">
        <SkeletonLine className="w-16" />
        <SkeletonLine className="w-full" />
        <SkeletonLine className="w-3/4" />
      </div>
    </div>
  );
}
