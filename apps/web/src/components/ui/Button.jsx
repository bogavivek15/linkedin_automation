import React from 'react';
import { cn } from '../../utils/cn';

export function Button({
  className,
  variant = 'default',
  size = 'default',
  children,
  ...props
}) {
  const baseStyles = "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]";

  const variants = {
    default: "bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm shadow-indigo-500/20",
    secondary: "bg-zinc-800 text-zinc-200 hover:bg-zinc-700 border border-zinc-700/50",
    outline: "border border-zinc-700 text-zinc-300 hover:bg-zinc-800/80 hover:text-white",
    ghost: "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60",
    danger: "bg-red-600/90 text-white hover:bg-red-500 shadow-sm shadow-red-500/20",
  };

  const sizes = {
    sm: "text-xs px-2.5 py-1.5 gap-1.5",
    default: "text-sm px-4 py-2 gap-2",
    lg: "text-base px-5 py-2.5 gap-2.5",
    icon: "h-9 w-9 p-0",
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  );
}
