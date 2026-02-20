<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<nav>
	<a href="/">Map Poster</a>
	<a href="/builder">Builder</a>
	<a href="/mon-classement">Mon classement</a>
</nav>

<main>
	{@render children()}
</main>

<style>
	nav {
		display: flex;
		gap: 1rem;
		padding: 1rem;
		border-bottom: 1px solid #e5e5e5;
		margin-bottom: 1rem;
	}

	main {
		padding: 0 1rem 1rem;
	}
</style>
