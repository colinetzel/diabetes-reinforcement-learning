// GlucoSym POST script, coupled with SARSA

var glucoURL = "http://localhost:3000/dose";
var request = require("sync-request");

// Glucosym response
var response;

// Initialize the Q function matrix
// Q = [S][A] = [glucose][timeSinceLastMeal][basal][bolus]
var Q = new Array(300).fill(new Array(2880).fill(new Array(100).fill(new Array(100).fill(0))));

// Outer loop simulates different days; episodes
for (ep = 0; ep < 20; ep++)
{
    var postdata = { "dose": 0.0, "dt": 5, "index": 0, "time": 1440, "events": { "bolus": [{ "amt": 0.0, "start": 0 }], "basal": [{ "amt": 0.0, "start": 0, "length": 0 }], "carb": [{ "amt": 0.0, "start": 0, "length": 0 }] } };
    // Initial post to get glucose at start of day
    response = request('POST', glucoURL, { json: postdata });

    // Set current and last glucose same initially, to avoid initial bolus
    var glucose = (JSON.parse(response.getBody())).bg;
    var lastGlucose = glucose;

    var timeSinceLastMeal = 720;
    var prevTimeSinceLastMeal = timeSinceLastMeal; 

    // Randomly pick meal times from range of normal meal times
    var breakfastTime = randomIntFromInterval(480, 540);
    var lunchTime = randomIntFromInterval(720, 840);
    var dinnerTime = randomIntFromInterval(1020, 1200);

    var breakfast = false;
    var lunch = false;
    var dinner = false;

    // SARSA; choose initial action
    var maxVal = max(Q, Math.round(glucose), timeSinceLastMeal);
    var basalInject = maxVal[0];
    var bolusInject = maxVal[1]; 
    var alpha = 1;

    var episodeLost = false;

    // Inner loop simulates time throughout single day/episode
    for (t = 5; t <= 1440; t += 5)
    {
        //console.log(glucose);
        var curIndex = t / 5;

        // Simulate killing patient
        if (Math.round(glucose) >= 300)
        {
            // Induced extreme hyperglycemia: Patient killed
            episodeLost = true;
            break;
        }
        if (Math.round(glucose) <= 70)
        {
            // Induced extreme hypoglycemia: Patient killed
            episodeLost = true;
            break;
        }

        // Measured in grams
        var carbs = 0;

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

        // Determine reward for this state
        var r = 0;

        if (glucose > 70 && glucose < 100)
            r = Math.floor(Math.log(glucose - 70) - 4);
        if (glucose <= 70)
            r = -1000;
        if (glucose > 180)
            r = 0;
        if (glucose >= 100 && glucose <= 180)
            r = 1; 

        // Prepare to post this timestep's data to the simulator
        var postdata = { "dose": basalInject + bolusInject, "dt": 5, "index": curIndex, "time": 1440, "events": { "bolus": [{ "amt": bolusInject, "start": t }], "basal": [{ "amt": basalInject, "start": t, "length": 600 }], "carb": [{ "amt": carbs, "start": 0, "length": 90 }] } };

        // Post this timestep and get result for next timestep
        response = request('POST', glucoURL, { json: postdata });
 
        // Simulate losing the episode
        if (Math.round( (JSON.parse(response.getBody())).bg ) >= 300 || Math.round( (JSON.parse(response.getBody())).bg ) <= 70)
        {
            episodeLost = true;
            Q[Math.round(glucose)][timeSinceLastMeal][basalInject][bolusInject] = -100;
            break;
        }

        // Pick next best action from s'
        var basalPrime = 0;
        var bolusPrime = 0;
        var maxVal = max(Q, Math.round( (JSON.parse(response.getBody())).bg ), timeSinceLastMeal + 5);
        basalPrime = maxVal[0];
        bolusPrime = maxVal[1];

        // Perform Q update
        Q[Math.round(glucose)][timeSinceLastMeal][basalInject][bolusInject] = SARSA(Q[Math.round(glucose)][timeSinceLastMeal][basalInject][bolusInject], r, Q[Math.round( (JSON.parse(response.getBody())).bg  )][timeSinceLastMeal + 5][basalPrime][bolusPrime], alpha);

        // Update s and s' values
        lastGlucose = glucose;
        prevTimeSinceLastMeal = timeSinceLastMeal;

        glucose = (JSON.parse(response.getBody())).bg;

        // 5 minutes since last observation, thus 5 minutes added to last meal observation
        timeSinceLastMeal += 5;

        // Update alpha
        alpha = 1.0 / t;
    }

    // Last post to end this simulation
    response = request('POST', 'http://localhost:3000/', { json: {} });
}

function randomIntFromInterval(min, max) {
    var sum = 0;
    for (var i = 0; i < 6; i++)
        sum += Math.random() * (max - min + 1) + min;
    return Math.floor(sum/6);    
}

function SARSA(q, r, qPrime, alpha) {
    q = q + alpha * (r + 0.9 * qPrime - q);
    return q;
}

function max(q, glucose, timeSinceMeal) {
    var maxQ = -10000000;
    var maxBasal = 0;
    var maxBolus = 0;

    for (var i = 0; i < 100; i++) {
        for (var j = 0; j < 100; j++) {
            if (q[glucose][timeSinceMeal][i][j] > maxQ) {
                maxQ = q[glucose][timeSinceMeal][i][j];
                maxBasal = i;
                maxBolus = j;
            }
        }
    }
    console.log(maxQ);
    return [maxBasal, maxBolus];
}
