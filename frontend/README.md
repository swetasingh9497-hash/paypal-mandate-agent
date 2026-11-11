# Budgie

AI proposes. Code decides.

A frontend for an AI shopping agent that buys within your limits and pays with PayPal.

## Tech Stack

- TanStack Start (React + SSR)
- TypeScript
- React 18
- Tailwind CSS
- TanStack Router
- TanStack Query
- Framer Motion

## Development

```sh
# Install dependencies
bun install

# Start dev server
bun run dev

# Build for production
bun run build
```

## Structure

```
src/
├── components/
│   ├── mandate/       # Budgie-specific components
│   └── ui/            # Reusable UI components (shadcn-style)
├── lib/
│   ├── api.ts         # API client (demo + live)
│   ├── auth.ts        # Local auth provider
│   ├── spending.ts    # Spending normalization & types
│   └── mock*.ts       # Mock data for demo mode
├── routes/
│   ├── __root.tsx     # Root layout, head meta, providers
│   ├── index.tsx      # Home page (mandate input + results)
│   └── spending.tsx   # Spending history page
└── styles.css         # Global styles & Tailwind
```

## Demo Mode

Toggle "Demo data" in the header to explore with a sandbox account (`demo@budgie.app`). No network calls are made in demo mode.

## License

MIT