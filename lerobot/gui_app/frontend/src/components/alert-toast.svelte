<script>
import { alertMessages } from '../stores/alert-msg-store';
import { onDestroy } from 'svelte';

let msg = "";
let showToast = false;
let timer;

// subscribe to alertMessages store and react whenever a new error is added
const unsubscribe = alertMessages.subscribe((errors) => {
    if (errors.length > 0) {
        msg = errors[errors.length - 1];
        showToast = true;
        
        // auto-hide after 5 seconds
        clearTimeout(timer);
        timer = setTimeout(() => {
            showToast = false;
        }, 5000);
    }
});

onDestroy(() => {
    clearTimeout(timer);
    unsubscribe();
});
</script>
    
{#if showToast}
<div class="toast show bg-success-subtle position-fixed bottom-0 end-0 p-2 m-3" role="alert" aria-live="assertive" aria-atomic="true" style="min-width: 250px;">
    <div class="toast-header bg-success-subtle">
        <img src="/static/images/lerobot-icon.webp" class="rounded me-2" alt="lerobot logo" style="width: 20px; height:20px">
        <strong class="me-auto">Alert</strong>
        <small>Just now</small>
        <button type="button" class="btn-close" aria-label="Close" onclick={() => (showToast = false)}></button>
    </div>
    <div class="toast-body mt-2">{msg}</div>
</div>
{/if}
      