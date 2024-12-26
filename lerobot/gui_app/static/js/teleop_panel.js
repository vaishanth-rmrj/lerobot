// js for teleop gui controls

document.getElementById("startTeleopBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/select_mode/teleop", { method: "GET" });
    } catch (error) {
        console.error("Error starting teleoperation:", error);
    }
}); 

document.getElementById("stopTeleopBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping teleoperation:", error);
    }
});

document.getElementById('teleopConfigForm')
.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent the default form submission

    const formData = new FormData(teleopConfigForm);
    const response = await fetch(teleopConfigForm.action, {
        method: teleopConfigForm.method,
        body: formData
    });

    if (response.ok) {
        alert('Teleop configuration updated successfully');
    } else {
        alert('Error updating teleop configuration!!');
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("teleopConfigForm");

    try {
        // fetch data from the backend
        const response = await fetch("/robot/get-control-config/teleop");
        const data = await response.json();

        // map backend data to form fields
        form.robotConfigSelect.value = data.robot_config;
        form.teleopFPS.value = data.fps;        

    } catch (error) {
        console.error("Error fetching configuration data:", error);
    }
});