"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Search, CheckCircle, XCircle, AlertCircle, Loader2 } from "lucide-react"

export default function FactCheckerPage() {
  const [claim, setClaim] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<{
    verdict: "true" | "false" | "partially-true" | "unverifiable" | null
    explanation: string
    sources: string[]
  } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!claim.trim()) return

    setIsLoading(true)
    setResult(null)

    // Simulate API call - in production, this would call your fact-checking backend
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Mock result for demonstration
    setResult({
      verdict: "partially-true",
      explanation:
        "This claim contains elements of truth but lacks important context. While the core assertion has some factual basis, the full picture requires additional nuance and consideration of related factors.",
      sources: [
        "https://example.com/source1",
        "https://example.com/source2",
        "https://example.com/source3",
      ],
    })

    setIsLoading(false)
  }

  const getVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case "true":
        return <CheckCircle className="h-8 w-8 text-green-500" />
      case "false":
        return <XCircle className="h-8 w-8 text-red-500" />
      case "partially-true":
        return <AlertCircle className="h-8 w-8 text-amber-500" />
      default:
        return <AlertCircle className="h-8 w-8 text-muted-foreground" />
    }
  }

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case "true":
        return "text-green-600 bg-green-50 border-green-200"
      case "false":
        return "text-red-600 bg-red-50 border-red-200"
      case "partially-true":
        return "text-amber-600 bg-amber-50 border-amber-200"
      default:
        return "text-muted-foreground bg-muted border-border"
    }
  }

  const getVerdictLabel = (verdict: string) => {
    switch (verdict) {
      case "true":
        return "True"
      case "false":
        return "False"
      case "partially-true":
        return "Partially True"
      default:
        return "Unverifiable"
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-2xl">
          {/* Header */}
          <div className="mb-10 text-center">
            <h1 className="mb-3 text-4xl font-bold tracking-tight text-foreground">
              Cerebras Fact Checker
            </h1>
            <p className="text-lg text-muted-foreground">
              Verify claims with AI-powered fact checking
            </p>
          </div>

          {/* Search Form */}
          <Card className="mb-8">
            <CardContent className="pt-6">
              <form onSubmit={handleSubmit} className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type="text"
                    placeholder="Enter a claim to fact-check..."
                    value={claim}
                    onChange={(e) => setClaim(e.target.value)}
                    className="pl-10"
                    disabled={isLoading}
                  />
                </div>
                <Button type="submit" disabled={isLoading || !claim.trim()}>
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Checking
                    </>
                  ) : (
                    "Check"
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Loading State */}
          {isLoading && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Loader2 className="mb-4 h-12 w-12 animate-spin text-primary" />
                <p className="text-lg font-medium text-foreground">Analyzing claim...</p>
                <p className="text-sm text-muted-foreground">
                  Searching sources and verifying information
                </p>
              </CardContent>
            </Card>
          )}

          {/* Result */}
          {result && !isLoading && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-4">
                  {getVerdictIcon(result.verdict || "unverifiable")}
                  <div>
                    <CardTitle className="text-xl">Verdict</CardTitle>
                    <span
                      className={`mt-1 inline-block rounded-full border px-3 py-1 text-sm font-medium ${getVerdictColor(result.verdict || "unverifiable")}`}
                    >
                      {getVerdictLabel(result.verdict || "unverifiable")}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="mb-2 font-semibold text-foreground">Explanation</h3>
                  <p className="leading-relaxed text-muted-foreground">{result.explanation}</p>
                </div>

                {result.sources.length > 0 && (
                  <div>
                    <h3 className="mb-2 font-semibold text-foreground">Sources</h3>
                    <ul className="space-y-2">
                      {result.sources.map((source, index) => (
                        <li key={index}>
                          <a
                            href={source}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline"
                          >
                            {source}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Initial State */}
          {!result && !isLoading && (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <Search className="mb-4 h-12 w-12 text-muted-foreground/50" />
                <CardDescription className="text-base">
                  Enter a claim above to get started
                </CardDescription>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </main>
  )
}
