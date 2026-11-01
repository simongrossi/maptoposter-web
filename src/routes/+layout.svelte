<script lang="ts">
    import favicon from '$lib/assets/favicon.svg';
    import { page } from '$app/state';

    let { children } = $props();

    const navItems = [
        { href: '/builder', label: 'Builder' },
        { href: '/mon-classement', label: 'Mon classement' },
        { href: '/about', label: 'À propos' },
    ];

    let pathname = $derived(page.url.pathname);

    function isActive(href: string): boolean {
        return pathname === href || pathname.startsWith(`${href}/`);
    }
</script>

<svelte:head>
    <link rel="icon" href={favicon} />
    <meta name="theme-color" content="#0a0c10" />
</svelte:head>

{#if pathname === '/'}
    <main class="app-main">
        {@render children()}
    </main>
{:else}
    <div class="page-shell">
        <header class="site-header">
            <div class="header-inner">
                <a class="brand" href="/" aria-label="MapPoster, retour au générateur">
                    <span class="brand-mark">M</span>
                    <span class="brand-name">MAP<span>POSTER</span></span>
                </a>

                <nav aria-label="Navigation principale">
                    {#each navItems as item}
                        <a
                            href={item.href}
                            class:active={isActive(item.href)}
                            aria-current={isActive(item.href) ? 'page' : undefined}
                        >
                            {item.label}
                        </a>
                    {/each}
                </nav>

                <a class="header-cta" href="/">Générer une affiche</a>
            </div>
        </header>

        <main class="page-content">
            {@render children()}
        </main>

        <footer class="site-footer">
            <span>MapPoster · données © OpenStreetMap contributors</span>
            <a href="/about">Crédits & licence</a>
        </footer>
    </div>
{/if}

<style>
    :global(:root) {
        color-scheme: dark;
        --bg: #0a0c10;
        --bg-soft: #0f1319;
        --panel: #141922;
        --panel-2: #1a212c;
        --border: #26303c;
        --border-strong: #354252;
        --text: #f1f5f9;
        --muted: #95a3b3;
        --accent: #67e8f9;
        --accent-2: #60a5fa;
        --accent-3: #a78bfa;
        --success: #34d399;
        --danger: #fb7185;
        --radius: 16px;
        --shadow: 0 24px 80px rgba(0, 0, 0, 0.45);
        --font:
            "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    :global(*) {
        box-sizing: border-box;
    }

    :global(html) {
        scroll-behavior: smooth;
    }

    :global(body) {
        margin: 0;
        min-height: 100vh;
        min-height: 100dvh;
        color: var(--text);
        -webkit-text-size-adjust: 100%;
        text-size-adjust: 100%;
        background:
            radial-gradient(
                1200px 800px at 8% -10%,
                rgba(96, 165, 250, 0.12),
                transparent 60%
            ),
            radial-gradient(
                900px 600px at 100% 0%,
                rgba(103, 232, 249, 0.08),
                transparent 55%
            ),
            var(--bg);
        font-family: var(--font);
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }

    :global(a) {
        color: var(--accent);
    }

    :global(::selection) {
        background: rgba(103, 232, 249, 0.28);
        color: #fff;
    }

    :global(:focus-visible) {
        outline: 2px solid var(--accent);
        outline-offset: 2px;
    }

    :global(button),
    :global(input),
    :global(select),
    :global(textarea) {
        font: inherit;
    }

    :global(button),
    :global(a) {
        -webkit-tap-highlight-color: transparent;
    }

    :global(button) {
        touch-action: manipulation;
    }

    .app-main {
        height: 100vh;
        height: 100dvh;
        overflow: hidden;
    }

    .page-shell {
        min-height: 100vh;
        min-height: 100dvh;
        display: flex;
        flex-direction: column;
    }

    .site-header {
        position: sticky;
        top: 0;
        z-index: 50;
        padding-top: env(safe-area-inset-top);
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        background: rgba(10, 12, 16, 0.72);
        backdrop-filter: blur(18px);
    }

    .header-inner {
        width: min(1120px, 100% - 48px);
        min-height: 68px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        gap: 28px;
    }

    .brand {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        color: var(--text);
        text-decoration: none;
        font-weight: 800;
        letter-spacing: -0.03em;
    }

    .brand-mark {
        display: grid;
        place-items: center;
        width: 30px;
        height: 30px;
        border-radius: 9px;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: #06121a;
        font-size: 0.95rem;
        font-weight: 900;
        box-shadow: 0 6px 18px rgba(96, 165, 250, 0.28);
    }

    .brand-name {
        font-size: 1.05rem;
    }

    .brand-name span {
        color: var(--accent);
    }

    .site-header nav {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-left: auto;
    }

    .site-header nav a {
        padding: 8px 13px;
        border-radius: 999px;
        color: var(--muted);
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
        transition:
            color 0.18s ease,
            background 0.18s ease;
    }

    .site-header nav a:hover {
        color: var(--text);
        background: rgba(255, 255, 255, 0.055);
    }

    .site-header nav a.active {
        color: #06121a;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }

    .header-cta {
        padding: 9px 14px;
        border: 1px solid rgba(103, 232, 249, 0.35);
        border-radius: 999px;
        color: var(--accent);
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 600;
        white-space: nowrap;
        transition:
            background 0.18s ease,
            transform 0.18s ease;
    }

    .header-cta:hover {
        background: rgba(103, 232, 249, 0.1);
        transform: translateY(-1px);
    }

    .page-content {
        width: min(1120px, 100% - 48px);
        margin: 34px auto 72px;
        flex: 1;
    }

    .site-footer {
        width: min(1120px, 100% - 48px);
        margin: 0 auto;
        padding: 22px 0 calc(28px + env(safe-area-inset-bottom));
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 10px 16px;
        color: var(--muted);
        font-size: 0.8rem;
    }

    .site-footer a {
        color: var(--muted);
        text-decoration: none;
    }

    .site-footer a:hover {
        color: var(--accent);
    }

    @media (max-width: 760px) {
        .header-inner {
            width: min(1120px, 100% - 32px);
            min-height: 62px;
            gap: 14px;
        }

        .header-cta {
            display: none;
        }

        .site-header nav {
            gap: 0;
            overflow-x: auto;
            scrollbar-width: none;
        }

        .site-header nav::-webkit-scrollbar {
            display: none;
        }

        .site-header nav a {
            display: inline-flex;
            align-items: center;
            min-height: 44px;
            padding: 7px 9px;
            font-size: 0.82rem;
            white-space: nowrap;
        }

        .brand {
            min-height: 44px;
        }

        .brand-name {
            display: none;
        }

        .page-content,
        .site-footer {
            width: min(1120px, 100% - 32px);
        }

        .page-content {
            margin-top: 24px;
        }
    }
</style>
