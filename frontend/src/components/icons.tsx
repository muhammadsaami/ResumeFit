import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Base({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function DashboardIcon(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="3" y="3" width="7.5" height="8.5" rx="1.8" />
      <rect x="13.5" y="3" width="7.5" height="5.5" rx="1.8" />
      <rect x="3" y="14.5" width="7.5" height="6.5" rx="1.8" />
      <rect x="13.5" y="11.5" width="7.5" height="9.5" rx="1.8" />
    </Base>
  );
}

export function AnalysisIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
      <path d="M19 8.5V19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7.5L19 8.5Z" />
      <path d="M8.5 13.5h7M8.5 16.5h4" />
    </Base>
  );
}

export function MatchIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M10.5 13.5 4 20" />
      <path d="M13.5 10.5 20 4" />
      <circle cx="17" cy="7" r="3" />
      <circle cx="7" cy="17" r="3" />
      <path d="M4 5h4M5 3v4" />
    </Base>
  );
}

export function SparkIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M12 3.5 13.8 9l5.5 1.8-5.5 1.8L12 18.2l-1.8-5.6L4.7 10.8 10.2 9 12 3.5Z" />
      <path d="M18.5 15.5l.7 2.1 2.1.7-2.1.7-.7 2.1-.7-2.1-2.1-.7 2.1-.7.7-2.1Z" />
    </Base>
  );
}

export function ExportIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M12 3v11m0 0 3.5-3.5M12 14l-3.5-3.5" />
      <path d="M4.5 16.5v2.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2.5" />
    </Base>
  );
}

export function TemplatesIcon(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="3.5" y="4" width="17" height="16" rx="2.2" />
      <path d="M3.5 9h17M9 9v11" />
    </Base>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </Base>
  );
}

export function BellIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6Z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </Base>
  );
}

export function UserIcon(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M5 20a7 7 0 0 1 14 0" />
    </Base>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Base>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Base>
  );
}

export function UploadCloudIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M7 18a4 4 0 0 1-.5-7.97A5.5 5.5 0 0 1 17.4 9.3 3.5 3.5 0 0 1 17 18H7Z" />
      <path d="M12 13v6m0-6-2.3 2.3M12 13l2.3 2.3" />
    </Base>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M5 12.5 10 17l9-10" />
    </Base>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M12 4 2.5 20h19L12 4Z" />
      <path d="M12 10v4m0 3h.01" />
    </Base>
  );
}
