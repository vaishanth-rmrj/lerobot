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
        await fetch("/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping teleoperation:", error);
    }
});

document.getElementById('teleopConfigForm')
.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent the default form submission

    const formData = new FormData(teleopConfigForm);
    console.log(formData);
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

// TODO: modify implementation for teleop form
// document.addEventListener("DOMContentLoaded", async () => {
//     const form = document.getElementById("teleopConfigForm");

//     try {
//         // fetch data from the backend
//         const response = await fetch("/teleop/get-config");
//         const data = await response.json();

//         // map backend data to form fields
//         form.robotConfigSelect.value = data.robot_config;
//         form.recordFPS.value = data.fps;        

//     } catch (error) {
//         console.error("Error fetching configuration data:", error);
//     }
// });