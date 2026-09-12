import React from 'react';
import { cn } from '../../utils/cn';

export function Avatar({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full border border-zinc-700/60 bg-zinc-800",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function AvatarFallback({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-300",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
