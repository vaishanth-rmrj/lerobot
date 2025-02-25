<script>
import { onMount } from 'svelte';

let logs = $state([]);
let logsDisplay;

onMount(() => {
    const eventSource = new EventSource("/robot/stream-logs");

    eventSource.onmessage = (event) => {
        console.log("logs received!");
        logs = [...logs, event.data];

        if (event.data === "--- Streaming ended ---") {
            eventSource.close();
        }
    };

    eventSource.onerror = () => {
        console.log("Error occurred while streaming.");
        eventSource.close();
    };

    // Cleanup when component unmounts
    return () => {
        eventSource.close();
    };
});

$effect(() => {
    if (logsDisplay) {
        logsDisplay.scrollTop = logsDisplay.scrollHeight;
    }
});

</script>
  
<div class="card" style="background-color: var(--bs-gray-800)!important">
<div class="card-header">
    Logs
</div>
<div class="card-body">
    <div bind:this={logsDisplay} id="logsDisplay" style="overflow: scroll; min-height: 300px; max-height: 400px; font-size: 14px;">
    {#if logs.length === 0}
        <p>No messages logged</p>
    {:else}
        {#each logs as log}
        <div>{log}</div>
        {/each}
    {/if}
    </div>
</div>
</div>

<style>
#logsDisplay::-webkit-scrollbar {
    display: none;
}
</style>
  