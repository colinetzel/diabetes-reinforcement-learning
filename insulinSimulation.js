// GlucoSym POST script

// These are the arrays to track what is simulated
var States = [];
var Actions = [];
var Rewards = [];

var glucoURL = "http://localhost:3000/dose";
var request = require("sync-request");

// The JSON object that glucosym accepts
var postdata = { "dose": 0.0, "dt": 5, "index": 0, "time": 1440, "events": { "bolus": [{ "amt": 0.0, "start": 0 }], "basal": [{ "amt": 0.0, "start": 0, "length": 0 }], "carb": [{ "amt": 0.0, "start": 0, "length": 0 }] } };

// Glucosym response
var response;

// Outer loop simulates different days; episodes
for (ep = 0; ep < 1; ep++)
{
    // Initial post to get glucose at start of day
    response = request('POST', glucoURL, { json: postdata });

    // Set current and last glucose same initially, to avoid initial bolus
    var glucose = (JSON.parse(response.getBody())).bg;
    var lastGlucose = glucose;

    var timeSinceLastMeal = 720;

    // Randomly pick meal times from range of normal meal times
    var breakfastTime = randomIntFromInterval(480, 540);
    var lunchTime = randomIntFromInterval(720, 840);
    var dinnerTime = randomIntFromInterval(1020, 1200);

    var breakfast = false;
    var lunch = false;
    var dinner = false;

    // Inner loop simulates time throughout single day/episode
    for (t = 5; t <= 1440; t += 5)
    {
        console.log(glucose);

        // Current index in action, state, reward log
        var curIndex = t / 5;
        
        // Measured in International Units
        var insulinBasal = randomIntFromInterval(0, 100);
        var insulinBolus = 0;
        var carbs = 0;

        // If we observe a glucose spike, assume it was a meal. Bolus injection.
        if (glucose - lastGlucose >= 10)
        {
            // A change in bg that is larger than 10 mg/dl is considered a spike
            timeSinceLastMeal = 0;
            insulinBolus = randomIntFromInterval(0, 100);
        }

        // TODO: glucose NOT responding to carb injections
        // Simulate meals via carbohydrate injections at typical meal times
        if (breakfastTime == t || (t > breakfastTime && !breakfast))
        {
            // Measured in grams
            carbs = randomIntFromInterval(20, 60);
            breakfast = true;
        }

        if (lunchTime == t || (t > lunchTime && !lunch)) {
            // Measured in grams
            carbs = randomIntFromInterval(20, 60);
            lunch = true;
        }

        if (dinnerTime == t || (t > dinnerTime && !dinner)) {
            // Measured in grams
            carbs = randomIntFromInterval(20, 60);
            dinner = true;
        }

        // Log all of this timestep's RL info

        // The JSON object that stores state info
        var stateInfo = { "bloodGlucose": 0, "lastMealSeen": 0 };
        // The JSON object that stores action info
        var actionInfo = { "bolusInject": 0, "basalInject": 0 };

        stateInfo.bloodGlucose = glucose;
        stateInfo.lastMealSeen = timeSinceLastMeal;

        actionInfo.bolusInject = insulinBolus;
        actionInfo.basalInject = insulinBasal;

        States.push(stateInfo);
        Actions.push(actionInfo);

        // TODO: Add our actual reward function
        // Determine reward for this state
        if (glucose >= 70 && glucose <= 130)
            Rewards.push(1);
        if (glucose < 70)
            Rewards.push(-1);
        if (glucose > 130)
            Rewards.push(-1);

        // Prepare to post this timestep's data to the simulator
        var postdata = { "dose": insulinBasal + insulinBolus, "dt": 5, "index": curIndex, "time": 1440, "events": { "bolus": [{ "amt": insulinBolus, "start": t }], "basal": [{ "amt": insulinBasal, "start": t, "length": 600 }], "carb": [{ "amt": carbs, "start": t, "length": 90 }] } };

        // Post this timestep and get result for next timestep
        response = request('POST', glucoURL, { json: postdata });

        lastGlucose = glucose;

        glucose = (JSON.parse(response.getBody())).bg;

        // 5 minutes since last observation, thus 5 minutes added to last meal observation
        timeSinceLastMeal += 5;
    }
}

function randomIntFromInterval(min, max) {
    return Math.floor(Math.random() * (max - min + 1) + min);
}