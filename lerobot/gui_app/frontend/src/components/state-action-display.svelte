<script>
import { onMount } from 'svelte';

// reactive array to store the joint state and action rows
let rows = [];

onMount(() => {
    const eventSource = new EventSource('/robot/stream-state-action');
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (rows.length === 0) {
            rows = data;
        } else {
            rows = data.map(item => ({
                joint: item.joint,
                state: parseFloat(item.state).toFixed(2),
                action: parseFloat(item.action).toFixed(2)
            }));
        }
    };

    eventSource.onerror = (error) => {
        console.error("Error with EventSource:", error);
    };

    // cleanup the EventSource when the component is destroyed
    return () => {
        eventSource.close();
    };
});
</script>
  
<div class="m-4" style="max-width: 300px;">
<table class="table table-striped table-bordered">
    <thead>
    <tr>
        <th scope="col">Joint Name</th>
        <th scope="col">State</th>
        <th scope="col">Action</th>
    </tr>
    </thead>
    <tbody>
    {#each rows as row}
        <tr>
        <td>{row.joint}</td>
        <td>{row.state}</td>
        <td>{row.action}</td>
        </tr>
    {/each}
    </tbody>
</table>
</div>
  