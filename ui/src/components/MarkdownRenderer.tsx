import type React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeHighlight from "rehype-highlight"

interface MarkdownRendererProps {
  content: string
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        h1: ({ node, ...props }) => <h1 className="text-xl font-bold text-[#00E5FF] mt-4 mb-2" {...props} />,
        h2: ({ node, ...props }) => <h2 className="text-lg font-bold text-[#00E5FF] mt-3 mb-2" {...props} />,
        h3: ({ node, ...props }) => <h3 className="text-md font-bold text-[#00E5FF] mt-2 mb-1" {...props} />,
        a: ({ node, ...props }) => <a className="text-[#7B42F6] underline hover:text-[#00E5FF]" {...props} />,
        p: ({ node, ...props }) => <p className="my-2" {...props} />,
        ul: ({ node, ...props }) => <ul className="list-disc ml-6 my-2" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal ml-6 my-2" {...props} />,
        li: ({ node, ...props }) => <li className="my-1" {...props} />,
        code: ({ node, inline, ...props }) =>
          inline ? (
            <code className="bg-[#0A1128] px-1 py-0.5 rounded text-[#F5F5F7]" {...props} />
          ) : (
            <code className="block bg-[#0A1128] p-3 rounded my-2 text-[#F5F5F7] overflow-x-auto" {...props} />
          ),
        pre: ({ node, ...props }) => <pre className="bg-[#0A1128] p-3 rounded my-2 overflow-x-auto" {...props} />,
        blockquote: ({ node, ...props }) => (
          <blockquote className="border-l-4 border-[#00E5FF]/50 pl-4 italic my-2" {...props} />
        ),
        strong: ({ node, ...props }) => <strong className="font-bold" {...props} />,
        hr: ({ node, ...props }) => <hr className="my-4 border-[#00E5FF]/20" {...props} />,
        table: ({ node, ...props }) => <table className="min-w-full border-collapse my-4" {...props} />,
        th: ({ node, ...props }) => <th className="border border-[#00E5FF]/20 p-2 bg-[#121B30]" {...props} />,
        td: ({ node, ...props }) => <td className="border border-[#00E5FF]/20 p-2" {...props} />,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

export default MarkdownRenderer
