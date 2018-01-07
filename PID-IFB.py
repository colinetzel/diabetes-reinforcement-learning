# Author Colin Etzel
#/usr/bin/python3

import math
import random
import json
import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p", type=float, default=0.00465, help="Proportional PID component coefficent")
parser.add_argument("-i", type=float, default=0.0, help="Integral PID component coefficient")
parser.add_argument("-d", type=float, default=0.26156, help="Derivative component PID coefficient")
parser.add_argument("--ifb", action='store_true', help="Toggle for adding insulin feedback.")
parser.add_argument("--meals", action='store_true', help="Toggle for including carbs from simulated meals.")
parser.add_argument("--floor", type=float, default=0.0, help="Minimum amount of glucose produced (by liver in times of fasting)")
parser.add_argument("--target", type=int, default=120, help="Desired glucose value for algorithm to achieve")
parser.add_argument("--numDays", type=int, default=1, help="Number of days to run algorithm over.")

"""
The following constants are taken from:
Effect of Insulin Feedback on Closed-Loop Glucose Control: A Crossover Study by Ruiz et al.
https://www.ncbi.nlm.nih.gov/pubmed/23063039
"""

alpha11 = 0.9802 #subcutaneous insulin pharmokinetic constant 1
alpha21 = 0.014043 #subcutaneous insulin pharmokinetic constant 2
alpha31 = 0.000127 #subcutaneous insulin pharmokinetic constant 3

#pharmokinetic constant 1 is not present or used in the literature
alpha22 = 0.98582 #plasma insulin pharmokinetic constant 2
alpha32 = 0.017889 #plasma insulin pharmokinetic constant 3

alpha33 = 0.98198 #interstital insulin pharmokinetic constant 3

beta1 = 1.1881 #insulin delivery coefficient 1
beta2 = 0.0084741 #insulin delivery coefficient 2
beta3 = 0.00005 #insulin delivery coefficient 3

gamma1 = 0.64935 #IFB parameter for subcutaneous insulin 
gamma2 = 0.34128 #IFB parameter for plasma insulin
gamma3 = 0.0093667 #IFB parameter for effective insulin


def main():
    totalError = 0
    print("totalError assigned")

    # These are the arrays to track what is simulated
    States = []
    Actions = []
    Rewards = []

# Write headers to output file
    myFile = open("insulinResults.txt", "w")
    myFile.write("StateGlucose, StateTime, StateInsulin, ActionBasal, Reward, Step, Episode\n")

    glucoURL = "http://localhost:3000/dose"

    errors = []

    #Previous PID values for use by PID algorithm

    P = []
    I = []
    D = []

    FB = []

    totalInsulin = []
    initInsulin = 0

    args = parser.parse_args()

    Kp = args.p
    Ki = args.i
    Kd = args.d

    mealsPresent = args.meals
    useIFB = args.ifb

    targetGlucose = args.target
    basalFloor = args.floor
    numDays = args.numDays
    
    index = 0
    #The JSON object that glucosym accepts
    postdata = { "dose": 0.0, "dt": 5, "index": 0, "time": 1440, "events": { "basal": [{ "amt": 0.0, "start": 0, "length": 0 }], "carb": [{ "amt": 0.0, "start": 0, "length": 0 }] } }

    { "dose": 0.0, "dt": 5, "index": 0, "time": 1440, "events": { "basal": [{ "amt": 0.0, "start": 0, "length": 0 }], "carb": [{ "amt": 0.0, "start": 0, "length": 0 }] } };

    for ep in range(numDays):
        # Initial post to get glucose at start of day
        response = requests.post(glucoURL, json = postdata)
        obj = json.loads(response.text)

        Idosage = [0] #Insulin dosage
        Isubcutaneous = [0] #subcutaneous insulin estimates
        Iplasma = [0] #plasma insulin estimates
        Ieffective = [0] #effective/interstital insulin estimates

        # Set current and last glucose same initially
        if obj["bg"] != None:
            glucose = obj["bg"]

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

            #calculate subcutaneous insulin
            Isubcutaneous.append(Isc(Isubcutaneous[-1], Idosage[-1]))
            Iplasma.append(Ip(Isubcutaneous[-1], Iplasma[-1], Idosage[-1]))
            Ieffective.append(Ieff(Isubcutaneous[-1], Iplasma[-1],Ieffective[-1], Idosage[-1]))
            
            # Measured in International Units
            insulinBasal = 0


            if(useIFB):
                insulinBasal = max(basalFloor, PIDIDFAlgorithm(index, totalError, targetGlucose, lastGlucose, glucose, errors, t, Kp, Ki, Kd, P, I, D, Isubcutaneous[-1], Iplasma[-1], Ieffective[-1], FB))
            else:
                insulinBasal = max(basalFloor, PIDAlgorithm(index, totalError, targetGlucose, lastGlucose, glucose, errors, t, Kp, Ki, Kd, P, I, D))
            Idosage.append(insulinBasal)
            carbs = 0

            totalInsulin.append(Idosage[-1] + Isubcutaneous[-1] + Iplasma[-1] + Ieffective[-1])

            # Simulate meals via carbohydrate injections at typical meal times
            if (mealsPresent):
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
            stateInfo = { "bloodGlucose": 0, "lastMealSeen": 0, "totalInsulin": 0 }
            # The JSON object that stores action info
            actionInfo = { "basalInject": 0 }

            stateInfo["bloodGlucose"] = math.floor(glucose)
            stateInfo["lastMealSeen"] = timeSinceLastMeal
            stateInfo["totalInsulin"] = totalInsulin[-1]

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
            postdata = { "dose": insulinBasal, "dt": 5, "index": curIndex, "time": 1440, "events": { "basal": [{ "amt": insulinBasal, "start": t, "length": 5 }], "carb": [{ "amt": carbs, "start": 0, "length": 90 }] } }

            #Post this timestep and get result for next timestep
            response = requests.post(glucoURL, json = postdata)

            lastGlucose = glucose


            obj = json.loads(response.text)

            # Set current and last glucose same initially
            if obj["bg"] != None:
                glucose = obj["bg"]

            # 5 minutes since last observation, thus 5 minutes added to last meal observation
            timeSinceLastMeal += 5;

            #Increment loop variable by 5
            t = t + 5

            #debug statement
            if(useIFB):
                msg = "P: " + str(P[index]) + " I: " + str(I[index]) + " D: " + str(D[index]) + " IFB: " + str(FB[index]) + " Net: " + str(P[index] + I[index] + D[index] + FB[index])
            else:
                msg = "P: " + str(P[index]) + " I: " + str(I[index]) + " D: " + str(D[index]) + " Net: " + str(P[index] + I[index] + D[index])
            print(msg)

            #increment index
            index = index + 1
        
        #Write this episode to file
        for i in range(len(States)):
            myFile.write(str(States[i]["bloodGlucose"]) + ", " + str(States[i]["lastMealSeen"]) + ", " + str(States[i]["totalInsulin"]) + ", " + str(Actions[i]["basalInject"]) + ", " + str(Rewards[i]) + ", " + str(i) + ", " + str(ep) + "\n")


        # Last post to end this simulation
        response = requests.post('http://localhost:3000/')

        #empty lists for next day's simulation
        States = []
        Actions = []
        Rewards = []

        P = []
        I = []
        D = []

        totalInsulin = []

        FB = []

def errorSum(errorSum, previousError, currentError, dt):
    "Sums the error between the current step and the last step. An estimation that assumes linearity between steps."
    h = currentError - previousError
    newError = errorSum + dt*h/2 + previousError*dt
    return newError

def proportionalError(currentError, Kp):
    return currentError * Kp

def integralError(errorSum, dt, Ki):
    return errorSum * Ki

def derivativeError(slope, dt, Kd):
    return slope * dt * Kd

def PIDAlgorithm(stepIndex, totalError, targetGlucose, previousGlucose, currentGlucose, errors, dt, Kp, Ki, Kd, P, I, D):
    error = currentGlucose - targetGlucose
    try:
        totalError = errorSum(totalError, errors[-1], error, dt)
    except IndexError:
        totalError = errorSum(totalError, 0, error, dt)
    errors.append(error)

    P.append(proportionalError(error,Kp))
    I.append(integralError(totalError,dt,Ki))
    slope = (currentGlucose - previousGlucose) / dt
    D.append(derivativeError(slope,dt,Kd))

    correction = P[stepIndex] + I[stepIndex] + D[stepIndex]
    return correction

def PIDIDFAlgorithm(stepIndex, totalError, targetGlucose, previousGlucose, currentGlucose, errors, dt, Kp, Ki, Kd, P, I, D, Isc, Ip, Ieff, FB):
    return PIDAlgorithm(stepIndex, totalError, targetGlucose, previousGlucose, currentGlucose, errors, dt, Kp, Ki, Kd, P, I, D) - insulinFeedback(Isc, Ip, Ieff, FB)

def randomIntFromInterval(min, max):
    "Generates a pseudorandom value from a normal distribution with bounds (min, max)"
    sum = 0
    for i in range(6):
        #random.random generates a float from uniform distribution with bounds (0,1)
        sum = sum + random.random() * (max - min + 1) + min 
    return math.floor(sum/6.0)

def insulinFeedback( Isc, Ip, Ieff, FB):
    "calculate insulin feedback"
    feedback = gamma1 * Isc + gamma2 * Ip + gamma3 * Ieff
    FB.append(feedback)
    print("\n FB " + str(FB[-1]))
    return feedback

def Isc(Isc_previous, Id_previous):
    "estimate current subcutaneous insulin"
    return alpha11 * Isc_previous + beta1 * Id_previous

def Ip(Isc_previous, Ip_previous, Id_previous):
    "estimate current plasma insulin"
    return alpha21 * Isc_previous + alpha22 * Ip_previous + beta2 * Id_previous
    
def Ieff(Isc_previous, Ip_previous, Ieff_previous, Id_previous):
    "estimate current effective (interstital) insulin"
    return alpha31 * Isc_previous + alpha32 * Ip_previous + alpha33 * Ieff_previous + beta3 * Id_previous


main()