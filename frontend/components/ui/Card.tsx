import React from "react";
import clsx from "clsx";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  glass?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, hover = false, glass = true, ...props }, ref) => (
    <div
      ref={ref}
      className={clsx(
        "rounded-2xl border border-white/10 transition duration-300",
        glass && "bg-gradient-to-br from-slate-800/30 to-slate-900/30 backdrop-blur-sm",
        hover && "hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10",
        className
      )}
      {...props}
    />
  )
);

Card.displayName = "Card";

export const CardHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx("px-6 py-4 border-b border-white/10", className)} {...props} />
);

export const CardContent = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx("p-6", className)} {...props} />
);

export const CardFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx("px-6 py-4 border-t border-white/10 flex items-center gap-3", className)} {...props} />
);
