import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { Upload, Workflow, FileText, History, Moon, Sun, Boxes } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const nav = [
  { to: "/", label: "Upload", icon: Upload },
  { to: "/analysis", label: "Analysis", icon: Workflow },
  { to: "/preview", label: "Preview", icon: FileText },
  { to: "/history", label: "History", icon: History },
] as const;

function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", !light);
  }, [light]);

  return (
    <Button
      variant="ghost"
      size="sm"
      className="w-full justify-start gap-2 text-muted-foreground"
      onClick={() => setLight((value) => !value)}
      aria-label="Toggle colour theme"
    >
      {light ? <Sun /> : <Moon />}
      <span className="text-xs">{light ? "Light mode" : "Dark mode"}</span>
    </Button>
  );
}

export function Workspace({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="flex min-h-screen w-full">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-4 py-6 md:flex">
        <div className="flex items-center gap-2 px-2">
          <span className="flex size-8 items-center justify-center rounded-md bg-primary/15 text-primary">
            <Boxes className="size-4" />
          </span>
          <div>
            <p className="text-sm font-semibold tracking-tight">FormaFlow</p>
            <p className="ff-mono text-[10px] uppercase text-muted-foreground">pipeline engine</p>
          </div>
        </div>

        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {nav.map((item) => {
            const active = pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto space-y-3 border-t border-sidebar-border pt-4">
          <ThemeToggle />
          <p className="ff-mono px-3 text-[10px] text-muted-foreground">demo build · mock data</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 overflow-x-auto border-b border-border bg-background/80 px-4 py-3 backdrop-blur md:hidden">
          {nav.map((item) => {
            const active = pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs whitespace-nowrap",
                  active ? "bg-accent text-accent-foreground" : "text-muted-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </header>
        <main className="min-w-0 flex-1 px-5 py-8 md:px-10 md:py-10">{children}</main>
      </div>
    </div>
  );
}