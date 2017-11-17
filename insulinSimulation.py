# Andrew's glucosym POST script (insulinSimulation.js) adapted to python
#/usr/bin/python3

import math
import random
import json
import requests



def main():

    # These are the arrays to track what is simulated
    States = []
    Actions = []
    Rewards = []

# Write headers to output file
    myFile = open("insulinResults.txt", "a")
    myFile.write("StateGlucose, StateTime, ActionBasal, ActionBolus, Reward, Step, Episode\n")

    glucoURL = "http://localhost:3000/dose"
    
#var request = require("sync-request"); #need to find python version of http requests

#The JSON object that glucosym accepts
    postdata = { "dose": 0.0, "dt": 5, "index": 0, "time": 1440, "events": { "bolus": [{ "amt": 0.0, "start": 0 }], "basal": [{ "amt": 0.0, "start": 0, "length": 0 }], "carb": [{ "amt": 0.0, "start": 0, "length": 0 }] } }


    for ep in range(7):

        # Initial post to get glucose at start of day
        response = requests.post(glucoURL, json = postdata)
        obj = json.loads(response.text)

        # Set current and last glucose same initially, to avoid initial bolus
        if obj["bg"] != None:
            glucose = obj["bg"]
        print(glucose)

        lastGlucose = glucose
        timeSinceLastMeal = 720

        #Randomly pick meal times from range of normal meal times
        breakfastTime = randomIntFromInterval(480, 540)
        lunchTime = randomIntFromInterval(720, 840)
        dinnerTime = randomIntFromInterval(1020, 1200)

        breakfast = False
        lunch = False
        dinner = False

        # Inner loop simulates time throughout single day/episode

        t = 5
        
        #t increments by 5 at the end of the loop
        while t <= 1440:
            print(glucose)

            # Current index in action, state, reward log
            curIndex = t / 5
            
            # Measured in International Units
            insulinBasal = 0
            if t % 60 == 0:
                insulinBasal = randomIntFromInterval(0, 5)
            insulinBolus = 0
            carbs = 0

            #If we observe a glucose spike, assume it was a meal. Bolus injection.
            if (glucose - lastGlucose) >= 4:
                
                print(str(glucose) + "-" + str(lastGlucose) )
                #A change in bg that is larger than 10 mg/dl is considered a spike
                timeSinceLastMeal = 0
                insulinBolus = randomIntFromInterval(0, 5)
        

            # Simulate meals via carbohydrate injections at typical meal times
            if (breakfastTime == t) or (t > breakfastTime and not breakfast):
            
                #Measured in grams
                carbs = randomIntFromInterval(20, 60)
                breakfast = True
            

            if (lunchTime == t) or (t > lunchTime and not lunch):
                # Measured in grams
                carbs = randomIntFromInterval(20, 60)
                lunch = True
            

            if (dinnerTime == t) or (t > dinnerTime and not dinner):
                # Measured in grams
                carbs = randomIntFromInterval(20, 60)
                dinner = True
            

            # Log all of this timestep's RL info

            # The JSON object that stores state info
            stateInfo = { "bloodGlucose": 0, "lastMealSeen": 0 }
            # The JSON object that stores action info
            actionInfo = { "bolusInject": 0, "basalInject": 0 }

            stateInfo["bloodGlucose"] = math.floor(glucose)
            stateInfo["lastMealSeen"] = timeSinceLastMeal

            actionInfo["bolusInject"] = insulinBolus
            actionInfo["basalInject"] = insulinBasal

            States.append(stateInfo)
            Actions.append(actionInfo)

            # Determine reward for this state
            if (glucose > 70) and (glucose < 100):
                Rewards.append(math.floor(math.log(glucose - 70) - 4))
            if (glucose <= 70):
                Rewards.append(-1000)
            if (glucose > 180):
                Rewards.append(0)
            if (glucose >= 100) and (glucose <= 180):
                Rewards.append(1)

            # Prepare to post this timestep's data to the simulator
            postdata = { "dose": insulinBasal + insulinBolus, "dt": 5, "index": curIndex, "time": 1440, "events": { "bolus": [{ "amt": insulinBolus, "start": t }], "basal": [{ "amt": insulinBasal, "start": t, "length": 600 }], "carb": [{ "amt": carbs, "start": 0, "length": 90 }] } }

            #Post this timestep and get result for next timestep
            response = requests.post(glucoURL, json = postdata)

            lastGlucose = glucose


            obj = json.loads(response.text)

            # Set current and last glucose same initially, to avoid initial bolus
            if obj["bg"] != None:
                glucose = obj["bg"]

            # 5 minutes since last observation, thus 5 minutes added to last meal observation
            timeSinceLastMeal += 5;

            #Increment loop variable by 5
            t = t + 5
        
        #Write this episode to file
        for i in range(len(States)):
            myFile.write(str(States[i]["bloodGlucose"]) + ", " + str(States[i]["lastMealSeen"]) + ", " + str(Actions[i]["basalInject"]) + ", " + str(Actions[i]["bolusInject"]) + ", " + str(Rewards[i]) + ", " + str(i) + ", " + str(ep) + "\n")


        # Last post to end this simulation
        response = requests.post('http://localhost:3000/')
        States = []
        Actions = []
        Rewards = []


def randomIntFromInterval(min, max):
    "Generates a pseudorandom value from a normal distribution with bounds (min, max)"
    sum = 0
    for i in range(6):
        #random.random generates a float from uniform distribution with bounds (0,1)
        sum = sum + random.random() * (max - min + 1) + min 
    return math.floor(sum/6.0)

main()