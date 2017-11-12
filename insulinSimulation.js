// GlucoSym POST script

// These are the arrays to track what is simulated
var States = [];
var Actions = [];
var Rewards = [];

// Write headers to output file
var fs = require('fs');
fs.writeFile("insulinResults.txt", "StateGlucose, StateTime, ActionBasal, ActionBolus, Reward, Step, Episode\n");

var glucoURL = "http://localhost:3000/dose";
var request = require("sync-request");

// The JSON object that glucosym accepts
var postdata = { "dose": 0.0, "dt": 5, "index": 0, "time": 1440, "events": { "bolus": [{ "amt": 0.0, "start": 0 }], "basal": [{ "amt": 0.0, "start": 0, "length": 0 }], "carb": [{ "amt": 0.0, "start": 0, "length": 0 }] } };

// Glucosym response
var response;

// Outer loop simulates different days; episodes
for (ep = 0; ep < 7; ep++)
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
        var insulinBasal = 0;
        if (t % 60 == 0)
            insulinBasal = randomIntFromInterval(0, 5);
        var insulinBolus = 0;
        var carbs = 0;

        // If we observe a glucose spike, assume it was a meal. Bolus injection.
        if (glucose - lastGlucose >= 4)
        {
            //console.log(glucose + "-" + lastGlucose );
            // A change in bg that is larger than 10 mg/dl is considered a spike
            timeSinceLastMeal = 0;
            insulinBolus = randomIntFromInterval(0, 5);
        }

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

        stateInfo.bloodGlucose = Math.floor(glucose);
        stateInfo.lastMealSeen = timeSinceLastMeal;

        actionInfo.bolusInject = insulinBolus;
        actionInfo.basalInject = insulinBasal;

        States.push(stateInfo);
        Actions.push(actionInfo);

        // Determine reward for this state
        if (glucose > 70 && glucose < 100)
            Rewards.push(Math.floor(Math.log(glucose - 70) - 4));
        if (glucose <= 70)
            Rewards.push(-1000);
        if (glucose > 180)
            Rewards.push(0);
        if (glucose >= 100 && glucose <= 180)
            Rewards.push(1); 

        // Prepare to post this timestep's data to the simulator
        var postdata = { "dose": insulinBasal + insulinBolus, "dt": 5, "index": curIndex, "time": 1440, "events": { "bolus": [{ "amt": insulinBolus, "start": t }], "basal": [{ "amt": insulinBasal, "start": t, "length": 600 }], "carb": [{ "amt": carbs, "start": 0, "length": 90 }] } };

        // Post this timestep and get result for next timestep
        response = request('POST', glucoURL, { json: postdata });

        lastGlucose = glucose;

        glucose = (JSON.parse(response.getBody())).bg;

        // 5 minutes since last observation, thus 5 minutes added to last meal observation
        timeSinceLastMeal += 5;
    }
    // Write this episode to file
    for(var i = 0; i < States.length; i++)
    {
        fs.appendFile("insulinResults.txt", States[i].bloodGlucose + ", " + States[i].lastMealSeen + ", " + Actions[i].basalInject + ", " + Actions[i].bolusInject + ", " + Rewards[i] + ", " + i + ", " + ep + "\n");
    }

    // Last post to end this simulation
    response = request('POST', 'http://localhost:3000/', { json: {} });
    States = [];
    Actions = [];
    Rewards = [];
}

function randomIntFromInterval(min, max) {
    var sum = 0;
    for (var i = 0; i < 6; i++)
        sum += Math.random() * (max - min + 1) + min;
    return Math.floor(sum/6);    
}
