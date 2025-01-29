// js for record gui controls

document.getElementById("startHGDAggerSessionBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/select_mode/hg_dagger", { method: "GET" });
    } catch (error) {
        console.error("Error starting HG-DAgger session:", error);
    }
});

document.getElementById("stopHGDAggerSessionBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping HG-DAgger session:", error);
    }
});

document.getElementById("interruptPolicyBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/hg-dagger/event/interrupt_policy", { method: "GET" });
    } catch (error) {
        console.error("Error interrupting policy:", error);
    }
});

document.getElementById("takeControlBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/hg-dagger/event/take_control", { method: "GET" });
    } catch (error) {
        console.error("Error taking control of robot:", error);
    }
});

document.getElementById("giveControlBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/hg-dagger/event/give_control", { method: "GET" });
    } catch (error) {
        console.error("Error giving control to policy:", error);
    }
});

document.getElementById("finishHGDaggerRolloutBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/hg-dagger/event/finish_early", { method: "GET" });
    } catch (error) {
        console.error("Error finishing HG-DAgger rollout:", error);
    }
});

// document.getElementById("cancelHGDaggerRolloutBtn")
// .addEventListener("click", async () => {
//     try {
//         await fetch("/robot/hg-dagger/event/cancel", { method: "GET" });
//     } catch (error) {
//         console.error("Error cancelling HG-DAgger rollout:", error);
//     }
// });

// config form funcs
document.getElementById('HGDAggerConfigForm')
.addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData(HGDAggerConfigForm);
    const response = await fetch(HGDAggerConfigForm.action, {
        method: HGDAggerConfigForm.method,
        body: formData
    });

    if (response.ok) {
        alert('HG-DAgger configuration updated successfully');
    } else {
        alert('Error updating HG-DAgger configuration!!');
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("HGDAggerConfigForm");

    try {
        // fetch data from the backend
        const response = await fetch("/robot/get-control-config/hg_dagger");
        const data = await response.json();

        // map backend data to form fields
        form.robotConfigSelect.value = data.robot_config;
        form.HGDAggerPolicyPath.value = data.pretrained_policy_path;
        form.HGDAggerRoot.value = data.root;
        // check if record root exists
        checkHGDAggerRootDirExists(data.root);

        form.HGDAggerRepoID.value = data.repo_id;
        form.HGDAggerFPS.value = data.fps;

        form.resumeHGDAggerProcessToggle.checked = data.resume;
        form.HGDAggerLocalFilesToggle.checked = data.local_files_only;
        form.HGDAggerRunComputeStats.checked = data.run_compute_stats;
        form.HGDAggerPushToHub.checked = data.push_to_hub;

        form.HGDAggerNumEpochs.value = data.num_epochs;
        form.HGDAggerCurrEpoch.value = data.curr_epoch;
        form.HGDAggerNumRollouts.value = data.num_rollouts;
        form.HGDAggerMaxRolloutTime.value = data.max_rollout_time_s;
        form.HGDAggerWarmupTime.value = data.warmup_time_s;
        form.HGDAggerResetTime.value = data.reset_time_s;

        form.HGDAggerImageWriterProcesses.value = data.num_image_writer_processes;
        form.HGDAggerImageWriterThreads.value = data.num_image_writer_threads_per_camera;
        form.HGDAggerSingleTask.value = data.single_task;

    } catch (error) {
        console.error("Error fetching record configuration data:", error);
    }
});

document.getElementById("HGDAggerRoot").addEventListener("input", async (event) => {
    const dirPath = event.target.value;
    checkHGDAggerRootDirExists(dirPath);
    
});

async function checkHGDAggerRootDirExists(dirPath) {
    const response = await fetch('/api/check-directory-exists', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ dir_path: dirPath })
    });
    if (!response.ok) {
        console.error("Failed to fetch directory status");
        return;
    }
    const data = await response.json();
    const dirNotExistsMsg = document.getElementById("HGDAggerDirNotExistsMsg");

    if (data.exists) {
        dirNotExistsMsg.style.display = "none";
    } else {
        dirNotExistsMsg.style.display = "block";
    }
}