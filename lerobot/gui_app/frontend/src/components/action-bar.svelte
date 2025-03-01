<script>
// Function to handle resetting the robot
function resetRobot() {
    fetch("/robot/reset", { method: "GET" })
    .then(response => response.json())
    .catch(error => {
        console.error('Error reinitializing robot on backend:', error);
    });
}

// Function to handle homing the robot
function homeRobot() {
    fetch("/api/home-robot", { method: "GET" })
    .then(response => response.json())
    .catch(error => {
        console.error('Error homing robot on backend:', error);
    });
}
function setHomePose() {
    fetch("/api/set-home-pose", { method: "GET" })
        .then(response => response.json())
        .catch(error => {
            console.error('Error setting home position on backend:', error);
    });
}
</script>
  
<div class="container mb-3 border rounded-2 p-4">
    <div class="btn-group me-2" role="group">
        <button 
            class="btn btn-outline-danger" 
            data-bs-title="Move robot to its home position" 
            data-bs-toggle="tooltip" 
            data-bs-placement="bottom"
            onclick={homeRobot}>
            Home Robot
        </button>
        <button 
            class="btn btn-outline-danger"
            type="button" 
            data-bs-title="Set robot's home position" 
            data-bs-toggle="tooltip" 
            data-bs-placement="bottom"
            onclick={setHomePose}>
            Set
        </button>
    </div>

    <button 
        class="btn btn-outline-warning" 
        id="resetRobotBtn"
        data-bs-toggle="tooltip" 
        data-bs-placement="bottom" 
        data-bs-title="Reset robot instance"
        onclick={resetRobot}>
        Reset Robot
    </button>
</div>
  