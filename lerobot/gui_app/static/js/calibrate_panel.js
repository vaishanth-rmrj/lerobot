document.addEventListener('DOMContentLoaded', function() {
    fetch('/robot/calibrate/get-arms-name')
        .then(response => response.json())
        .then(data => {
            const armList = document.getElementById('calibrateAvailableArms');
            if (data.length > 0) {
                armList.innerHTML = ''; // Clear existing content
            }

            data.forEach(arm => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item p-3';
                listItem.style.backgroundColor = 'var(--bs-gray-800)!important';

                const div = document.createElement('div');
                div.className = 'd-flex justify-content-between align-items-center';

                const strong = document.createElement('strong');
                strong.textContent = arm;

                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'btn btn-warning btn-sm';
                button.textContent = 'Calibrate';
                button.id = `calibrate_${arm}`; // Add unique id
                // Add event listener to the button
                button.addEventListener('click', function() {
                    calibrateArm(arm);
                });

                div.appendChild(strong);
                div.appendChild(button);
                listItem.appendChild(div);
                armList.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error fetching arm names:', error));
});

// make API call to calibrate the arm
function calibrateArm(arm_name) {
    fetch(`/robot/calibrate/${arm_name}`, {
        method: 'GET'
    })
    .then(response => {
        if (response.ok) {
            console.log(`Successfully calibrated ${arm}`);
        } else {
            console.error(`Failed to calibrate ${arm}`);
        }
    })
    .catch(error => console.error('Error during calibration:', error));
}

document.getElementById("stopCalibration")
.addEventListener("click", async () => {
    try {
        await fetch("/robot/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping arm calibration:", error);
    }
});


document.addEventListener('DOMContentLoaded', function() {
    fetch('/robot/calibrate/get-connected-cams-port')
        .then(response => response.json())
        .then(data => {
            const availableCameras = document.getElementById('availableCameras');
            if (data.length > 0) {
                availableCameras.innerHTML = ''; // Clear existing content
            }

            counter = 0;
            data.forEach(camera => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item p-3';
                listItem.style.backgroundColor = 'var(--bs-gray-800)!important';

                const div = document.createElement('div');
                div.className = 'd-flex justify-content-between';

                const cameraName = document.createElement('strong');
                cameraName.textContent = `Camera${counter}`;

                const cameraIndex = document.createElement('strong');
                cameraIndex.textContent = `Index: ${camera.index}`;

                const cameraPort = document.createElement('strong');
                cameraPort.textContent = `Port: ${camera.port}`;

                div.appendChild(cameraName);
                div.appendChild(cameraIndex);
                div.appendChild(cameraPort);
                listItem.appendChild(div);
                availableCameras.appendChild(listItem);

                counter++;
            });
        })
        .catch(error => console.error('Error fetching camera data:', error));
});