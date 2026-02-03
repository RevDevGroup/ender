import { cn } from "@/lib/utils"

/**
 * Code block syntax highlighting colors.
 * These match the CSS variables defined in index.css
 */
export const codeColors = {
  bg: '#262420',
  text: '#f5f1eb',
  comment: '#78746e',
  string: '#e9a86c',
  keyword: '#e94d1f',
  function: '#f5f1eb',
  variable: '#d4d0ca',
  punctuation: '#a8a49e',
} as const

interface CodeBlockProps {
  children: string
  filename?: string
  className?: string
}

/**
 * CodeBlock Component
 *
 * A styled code block with optional filename header.
 * For syntax highlighting, use with a library like Prism or highlight.js.
 *
 * @example
 * <CodeBlock filename="example.sh">
 *   npm install
 * </CodeBlock>
 */
export function CodeBlock({ children, filename, className }: CodeBlockProps) {
  return (
    <div className={cn("code-block", className)}>
      {filename && (
        <div className="code-filename">
          {filename}
        </div>
      )}
      <pre>
        <code>{children}</code>
      </pre>
    </div>
  )
}

interface InlineCodeProps {
  children: React.ReactNode
  className?: string
}

/**
 * InlineCode Component
 *
 * For inline code snippets within text.
 *
 * @example
 * <p>Run <InlineCode>npm install</InlineCode> to install dependencies.</p>
 */
export function InlineCode({ children, className }: InlineCodeProps) {
  return (
    <code className={cn(
      "bg-muted px-1.5 py-0.5 rounded text-sm font-mono",
      className
    )}>
      {children}
    </code>
  )
}
