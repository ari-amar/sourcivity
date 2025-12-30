import { cn } from '../lib/utils';

interface Props extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'success' | 'warning' | 'purple' | 'orange' | 'gray' | 'darkGreen';
}

const badgeVariants = {
  default: 'bg-primary text-primary-foreground',
  destructive: 'bg-destructive text-destructive-foreground',
  outline: 'border border-input bg-background text-foreground',
  secondary: 'bg-secondary text-secondary-foreground',
  success: 'bg-green-500 text-white',
  warning: 'bg-yellow-500 text-white',
  purple: 'bg-purple-500 text-white',
  orange: 'bg-orange-500 text-white',
  gray: 'bg-gray-500 text-white',
  darkGreen: 'bg-green-700 text-white',
};

export const Badge = ({
  variant = 'default',
  className,
  children,
  ...props
}: Props) => {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        badgeVariants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
