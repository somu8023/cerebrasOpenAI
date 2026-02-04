"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ArrowRight,
  Sparkles,
  Shield,
  Zap,
  ExternalLink,
} from "lucide-react"

export default function FactCheckerPage() {
  const [claim, setClaim] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<{
    verdict: "true" | "false" | "partially-true" | "unverifiable" | null
    explanation: string
    sources: { title: string; url: string }[]
    confidence: number
  } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!claim.trim()) return

    setIsLoading(true)
    setResult(null)

    await new Promise((resolve) => setTimeout(resolve, 2500))

    setResult({
      verdict: "partially-true",
      explanation:
        "This claim contains elements of truth but lacks important context. While the core assertion has some factual basis, the full picture requires additional nuance and consideration of related factors that significantly impact its accuracy.",
      confidence: 78,
      sources: [
        { title: "Reuters Fact Check", url: "https://reuters.com/fact-check" },
        { title: "Associated Press", url: "https://apnews.com" },
        { title: "PolitiFact Analysis", url: "https://politifact.com" },
      ],
    })

    setIsLoading(false)
  }

  const getVerdictConfig = (verdict: string) => {
    switch (verdict) {
      case "true":
        return {
          icon: CheckCircle2,
          label: "Verified True",
          color: "text-emerald-400",
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/20",
          glow: "shadow-emerald-500/20",
        }
      case "false":
        return {
          icon: XCircle,
          label: "False",
          color: "text-red-400",
          bg: "bg-red-500/10",
          border: "border-red-500/20",
          glow: "shadow-red-500/20",
        }
      case "partially-true":
        return {
          icon: AlertTriangle,
          label: "Partially True",
          color: "text-amber-400",
          bg: "bg-amber-500/10",
          border: "border-amber-500/20",
          glow: "shadow-amber-500/20",
        }
      default:
        return {
          icon: HelpCircle,
          label: "Unverifiable",
          color: "text-zinc-400",
          bg: "bg-zinc-500/10",
          border: "border-zinc-500/20",
          glow: "shadow-zinc-500/20",
        }
    }
  }

  const features = [
    {
      icon: Zap,
      title: "Lightning Fast",
      description: "Powered by Cerebras inference",
    },
    {
      icon: Shield,
      title: "Trusted Sources",
      description: "Cross-referenced verification",
    },
    {
      icon: Sparkles,
      title: "AI-Powered",
      description: "Advanced language models",
    },
  ]

  return (
    <main className="relative min-h-screen overflow-hidden bg-background">
      {/* Subtle grid background */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--border))_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border))_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-30" />

      {/* Gradient orb */}
      <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">
        <div className="h-[600px] w-[600px] rounded-full bg-gradient-to-b from-zinc-800/40 to-transparent blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto max-w-4xl px-6 py-20">
        {/* Header */}
        <header className="mb-16 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-4 py-1.5 text-sm text-muted-foreground backdrop-blur-sm">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Powered by Cerebras AI</span>
          </div>
          <h1 className="mb-4 text-balance text-5xl font-bold tracking-tight text-foreground md:text-6xl">
            Verify any claim
            <br />
            <span className="text-muted-foreground">in seconds.</span>
          </h1>
          <p className="mx-auto max-w-xl text-lg leading-relaxed text-muted-foreground">
            AI-powered fact-checking that searches trusted sources and delivers
            accurate verdicts with full transparency.
          </p>
        </header>

        {/* Search Form */}
        <div className="mb-12">
          <form onSubmit={handleSubmit} className="relative">
            <div className="group relative overflow-hidden rounded-2xl border border-border bg-card/80 p-2 backdrop-blur-sm transition-all duration-300 focus-within:border-zinc-600 focus-within:shadow-lg focus-within:shadow-zinc-900/50">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-secondary">
                  <Search className="h-5 w-5 text-muted-foreground" />
                </div>
                <Input
                  type="text"
                  placeholder="Enter a claim to fact-check..."
                  value={claim}
                  onChange={(e) => setClaim(e.target.value)}
                  disabled={isLoading}
                  className="h-12 flex-1 border-0 bg-transparent text-lg placeholder:text-muted-foreground/60 focus-visible:ring-0"
                />
                <Button
                  type="submit"
                  disabled={isLoading || !claim.trim()}
                  className="h-12 gap-2 rounded-xl px-6 text-base font-medium transition-all duration-200 hover:scale-[1.02] disabled:opacity-50"
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      <span>Analyzing</span>
                    </div>
                  ) : (
                    <>
                      <span>Check</span>
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          </form>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="animate-in rounded-2xl border border-border bg-card/80 p-8 backdrop-blur-sm">
            <div className="flex flex-col items-center justify-center py-8">
              <div className="relative mb-6">
                <div className="h-16 w-16 rounded-full border-2 border-zinc-700" />
                <div className="absolute inset-0 h-16 w-16 animate-spin rounded-full border-2 border-transparent border-t-foreground" />
              </div>
              <p className="mb-2 text-xl font-medium text-foreground">
                Analyzing claim...
              </p>
              <p className="text-muted-foreground">
                Searching trusted sources and verifying information
              </p>
              <div className="mt-6 flex gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Gathering sources
                </span>
                <span className="flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" style={{ animationDelay: "0.2s" }} />
                  Cross-referencing
                </span>
                <span className="flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-zinc-500" style={{ animationDelay: "0.4s" }} />
                  Generating verdict
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Result */}
        {result && !isLoading && (
          <div className="animate-in space-y-6">
            {/* Verdict Card */}
            <div
              className={`rounded-2xl border ${getVerdictConfig(result.verdict || "unverifiable").border} ${getVerdictConfig(result.verdict || "unverifiable").bg} p-8 shadow-xl ${getVerdictConfig(result.verdict || "unverifiable").glow}`}
            >
              <div className="mb-6 flex items-start justify-between">
                <div className="flex items-center gap-4">
                  {(() => {
                    const config = getVerdictConfig(result.verdict || "unverifiable")
                    const IconComponent = config.icon
                    return (
                      <div className={`rounded-xl ${config.bg} p-3`}>
                        <IconComponent className={`h-8 w-8 ${config.color}`} />
                      </div>
                    )
                  })()}
                  <div>
                    <p className="mb-1 text-sm font-medium uppercase tracking-wider text-muted-foreground">
                      Verdict
                    </p>
                    <p
                      className={`text-2xl font-bold ${getVerdictConfig(result.verdict || "unverifiable").color}`}
                    >
                      {getVerdictConfig(result.verdict || "unverifiable").label}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="mb-1 text-sm font-medium uppercase tracking-wider text-muted-foreground">
                    Confidence
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {result.confidence}%
                  </p>
                </div>
              </div>

              {/* Confidence bar */}
              <div className="mb-6 h-2 overflow-hidden rounded-full bg-secondary">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${
                    result.verdict === "true"
                      ? "bg-emerald-500"
                      : result.verdict === "false"
                        ? "bg-red-500"
                        : result.verdict === "partially-true"
                          ? "bg-amber-500"
                          : "bg-zinc-500"
                  }`}
                  style={{ width: `${result.confidence}%` }}
                />
              </div>

              <div>
                <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-muted-foreground">
                  Analysis
                </h3>
                <p className="text-lg leading-relaxed text-foreground/90">
                  {result.explanation}
                </p>
              </div>
            </div>

            {/* Sources Card */}
            {result.sources.length > 0 && (
              <div className="rounded-2xl border border-border bg-card/80 p-6 backdrop-blur-sm">
                <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-muted-foreground">
                  Sources Referenced
                </h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  {result.sources.map((source, index) => (
                    <a
                      key={index}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-center justify-between rounded-xl border border-border bg-secondary/50 p-4 transition-all duration-200 hover:border-zinc-600 hover:bg-secondary"
                    >
                      <span className="font-medium text-foreground">
                        {source.title}
                      </span>
                      <ExternalLink className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Initial State - Features */}
        {!result && !isLoading && (
          <div className="grid gap-4 sm:grid-cols-3">
            {features.map((feature, index) => (
              <div
                key={index}
                className="rounded-2xl border border-border bg-card/50 p-6 backdrop-blur-sm transition-all duration-200 hover:border-zinc-700 hover:bg-card/80"
              >
                <div className="mb-4 inline-flex rounded-xl bg-secondary p-3">
                  <feature.icon className="h-5 w-5 text-foreground" />
                </div>
                <h3 className="mb-1 font-semibold text-foreground">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <footer className="mt-20 text-center">
          <p className="text-sm text-muted-foreground">
            Built with Cerebras inference for lightning-fast AI responses
          </p>
        </footer>
      </div>
    </main>
  )
}
