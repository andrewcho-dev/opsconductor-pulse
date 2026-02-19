import type { SVGProps } from "react"

const baseProps: SVGProps<SVGSVGElement> = {
  xmlns: "http://www.w3.org/2000/svg",
  fill: "none",
  viewBox: "0 0 200 160",
  className: "w-full h-full",
}

/** Generic empty/no-data illustration — a cloud with dots */
export function IllustrationEmpty(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect
        x="30"
        y="20"
        width="140"
        height="120"
        rx="12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="4 4"
        opacity="0.2"
      />
      <path
        d="M70 100c-11 0-20-9-20-20s9-20 20-20c2-11 12-20 24-20 10 0 18 6 22 14 2-1 5-2 8-2 11 0 20 9 20 20s-9 20-20 20H70z"
        fill="currentColor"
        fillOpacity="0.04"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.15"
      />
      <circle cx="80" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="92" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="104" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="116" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="128" cy="118" r="2" fill="currentColor" opacity="0.15" />
    </svg>
  )
}

/** Setup/getting started — clipboard with checkmarks */
export function IllustrationSetup(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect
        x="30"
        y="20"
        width="140"
        height="120"
        rx="12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="4 4"
        opacity="0.2"
      />
      <rect
        x="70"
        y="35"
        width="60"
        height="80"
        rx="6"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.2"
        fill="currentColor"
        fillOpacity="0.03"
      />
      <rect
        x="85"
        y="30"
        width="30"
        height="12"
        rx="4"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.2"
        fill="currentColor"
        fillOpacity="0.05"
      />
      <line
        x1="82"
        y1="58"
        x2="118"
        y2="58"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.15"
      />
      <line
        x1="82"
        y1="72"
        x2="118"
        y2="72"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.15"
      />
      <line
        x1="82"
        y1="86"
        x2="110"
        y2="86"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.15"
      />
      <path
        d="M79 56l2 2 4-4"
        stroke="hsl(var(--primary))"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />
    </svg>
  )
}

/** Error/warning — triangle with exclamation */
export function IllustrationError(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect
        x="30"
        y="20"
        width="140"
        height="120"
        rx="12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="4 4"
        opacity="0.2"
      />
      <path
        d="M100 45L130 105H70L100 45z"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.2"
        fill="currentColor"
        fillOpacity="0.03"
      />
      <line
        x1="100"
        y1="65"
        x2="100"
        y2="85"
        stroke="currentColor"
        strokeWidth="2"
        opacity="0.3"
        strokeLinecap="round"
      />
      <circle cx="100" cy="95" r="2" fill="currentColor" opacity="0.3" />
    </svg>
  )
}

/** Search/not found — magnifying glass */
export function IllustrationNotFound(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect
        x="30"
        y="20"
        width="140"
        height="120"
        rx="12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="4 4"
        opacity="0.2"
      />
      <circle
        cx="95"
        cy="72"
        r="22"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.2"
        fill="currentColor"
        fillOpacity="0.03"
      />
      <line
        x1="112"
        y1="89"
        x2="128"
        y2="105"
        stroke="currentColor"
        strokeWidth="2"
        opacity="0.2"
        strokeLinecap="round"
      />
      <text
        x="95"
        y="78"
        textAnchor="middle"
        fill="currentColor"
        opacity="0.15"
        fontSize="20"
        fontWeight="600"
      >
        ?
      </text>
    </svg>
  )
}

