#!/usr/bin/python

from __future__ import print_function
import random
from initGame import initgame
from initNetwork import *
import tensorflow as tf
import numpy as np
from collections import deque

# implements various calculations
import nn_calc as nc

import math
import sys
import os
import time

# resolution of the images for the network
IMAGE_SIZE_X = 120
IMAGE_SIZE_Y = 120

# kernel size in pixel of the 3 concolutional layers
KERNEL1 = 5
KERNEL2 = 3
KERNEL3 = 2

# stride of the kernels in pixel (x & y)
STRIDE1 = 4
STRIDE2 = 2
STRIDE3 = 1

GAMMA = 0.95 # decay rate of past observations
OBSERVE = 32 # timesteps to observe before training
FINAL_EPSILON = 0.05 # final value of epsilon
INITIAL_EPSILON = 1#1.0 # starting value of epsilon
REPLAY_MEMORY = 590000 # number of previous transitions to remember
BATCH = 32 # size of minibatch
GAME = "Doom"
END = int( 2.5 * math.pow(10,6) ) # amount of actions to train
STORE = int( 0.01 * math.pow(10,6) ) # interval in which the parameters are stored

# for feedback and evaluate
IMG_STORED_INTERVAL = 1 # store current image every x frame
MAX_IMG_STORED = 0 # maximum amount of stored images
OBSERVE_EVALUATE = BATCH # set observe to the lowest value
REWARD_LOG_EVALUATE = 500 # interval to log the rewards
END_EVALUATE = 100000 # actions until the evaluation is stopped
SLEEPTIME = 0 # time between actions (for better visibility)

def trainNetwork(actions, num_actions, game, s, readout, h_fc1, sess, stack, frame_action, anneal_epsilon, with_depth, evaluate, feedback):
#==============================================================================
#
# variables:
# actions   array that contains the defined arrays for each action
# num_actions   amount of actions
# game      doom-game
# s         input-layer (80,80,?)-image
# readout   result of the network (Q), last layer of the network
# h_fc1     second-last layer of the network
# sess      tensorflow-session
#  
#==============================================================================

	# initialize values
    t = 1 # first turn
    t_last_save = 0 # last time the weights were stored 
    reward_p_turn = 0 # value for reward / action
    old_health = 0 # health @ last action
    reward_all = 0 # sum over all rewards
    crate_counter = 0 # overall collected crates (health-kits)

	# path to store the weights
    store_path = "logs_stack" + str(stack) + "_frame_action" + str(frame_action) + "_annealing" + str(anneal_epsilon) + "_withDepth" + str(with_depth)    
    if not os.path.exists(store_path):
        os.makedirs(store_path)        
        
	# path to sotre evaluation txt
    reward_path = store_path + "/reward.txt"

	# initialize feedback parameters, if flag is set
    if feedback:
        feedback_path = "feedback"
        if not os.path.exists(feedback_path):
            os.makedirs(feedback_path)
            os.makedirs(feedback_path + "/forVideo")
        qfile_path = feedback_path + "/qfile.txt"
        qfile = open(qfile_path, 'w')
        qfile.close()
        # qfile contains information for every action
        
        # current counter for feedback images
        imgcnt = 0
        # maximum amount of feedback images
        maximg = MAX_IMG_STORED
        
    
    #tensorflow variable for the actions
    a = tf.placeholder("float", [None, num_actions])
    #tensorflow variable for the target in the cost function
    y = tf.placeholder("float", [None])
    #multiply the action with the result of our network
    readout_action = tf.reduce_sum(tf.mul(readout, a), reduction_indices = 1)
    
    #cost function and gradient
    cost = tf.reduce_mean(tf.square(y - readout_action))
    train_step = tf.train.AdamOptimizer(1e-6).minimize(cost)
    
    # open up a game state to communicate with emulator
    game.new_episode()
    # get the game state
    game_state = game.get_state()
    
    # store the previous observations in replay memory
    D = deque()
    
    # create first image (grayscale)
    gray = nc.getGray(game_state)
    
    # create final image (if flag is set, with depth-image)
    if with_depth:
        depth = game_state.image_buffer[3,:,:]
        x_t = nc.image_postprocessing_depth(gray, depth, IMAGE_SIZE_Y, IMAGE_SIZE_X, False, t)
    else:
        x_t = nc.image_postprocessing(gray, IMAGE_SIZE_Y, IMAGE_SIZE_X, False, t)    
    
    # stack images
    s_t = nc.create_state(x_t, stack)
        
    # saver for the weights
    saver = tf.train.Saver(max_to_keep=100)
    # start session
    sess.run(tf.initialize_all_variables())
    
    # saving and loading weights
    checkpoint = tf.train.get_checkpoint_state(store_path)
    if checkpoint and checkpoint.model_checkpoint_path:
        saver.restore(sess, checkpoint.model_checkpoint_path)
        print("Successfully loaded:", checkpoint.model_checkpoint_path)
    else:
        print("Could not find old network weights, starting from scratch")
        
    # define learning parameters
    if evaluate:
		# no training => no random actions and no observations
        epsilon = FINAL_EPSILON
        observe = OBSERVE_EVALUATE
        end = END_EVALUATE + OBSERVE_EVALUATE
    else:
		# normal training
        observe = OBSERVE
        epsilon = INITIAL_EPSILON
        end = END
        
	# get current time
    start_time = time.time()

    print("************************* Running *************************")

	# training loop
    while "pigs" != "fly":

		# wait between actionsfor better visualization
        if evaluate:
            if SLEEPTIME >0:            
                time.sleep(SLEEPTIME)

        # get the Q-values of every action for the current state
        readout_t = readout.eval(feed_dict = {s : [s_t]})[0]
        # the zero makes an array out of the returend matrix (3,1)
        
        # choose random action or best action (dependent on epsilon)
        # if still observing, only random actions
        a_t =  [0] * num_actions
        action_index = 0
        if random.random() <= epsilon or t <= observe:
            action_index = random.randrange(num_actions)
            a_t[random.randrange(num_actions)] = 1
        else:
            action_index = np.argmax(readout_t)
            a_t[action_index] = 1
            
        # scale down epsilon (if finished observing)
        if epsilon > FINAL_EPSILON and t > OBSERVE:
            epsilon -= (INITIAL_EPSILON - FINAL_EPSILON) / anneal_epsilon
            if epsilon <= FINAL_EPSILON:
                print("Epsilon annealed to", epsilon, "%")
            
        # perform action and create new state (for K frames)
        for i in range(0, frame_action):
           
            # run the selected action and observe next state and reward
            r_t = game.make_action(a_t)
            
            # store if the episode terminated
            terminal = game.is_episode_finished()
            
            # restart the game if it terminated
            if game.is_episode_finished():
                game.new_episode()
                
            # get the new game state and the new image
            game_state = game.get_state()
            
            #get health and death_counter from game_state
            new_health = game_state.game_variables[0] 
            death_counter = game_state.game_variables[1]
            
            # calculate new reward values
            diff_health = float(new_health - old_health) # has to be conv. to float for game.set_living_reward()
            # if health increased => collected a crate (+25)
            # no positive reward if player died (player respawned with new health)
            if diff_health > 0 and not terminal:
                r_t = 25.0
                crate_counter += 1
                
			# update overall reward
            reward_all += r_t

            if feedback:
                print('t:',t)
                print("Q-values:", readout_t)
                print("Death counter:", death_counter)
                print("New Health:", new_health)
                print("Old Health:", old_health)
                print('Reward for this turn:',r_t)
                print("Diff Health:", diff_health)
                print("Terminal:", terminal)
                print("Crates collected:", crate_counter)
                print("Reward overall:", reward_all)
            
            # get image
            gray = nc.getGray(game_state)
            
            # add depth image if defined
            if with_depth:
                depth = game_state.image_buffer[3,:,:]
                # store filter images if feedback is true
                if feedback and t % IMG_STORED_INTERVAL == 0 and imgcnt < maximg:
                    x_t1 = nc.image_postprocessing_depth(gray, depth, IMAGE_SIZE_Y, IMAGE_SIZE_X, True, t)
                else:
                    x_t1 = nc.image_postprocessing_depth(gray, depth, IMAGE_SIZE_Y, IMAGE_SIZE_X, False, t)
            else:
                if feedback and t % IMG_STORED_INTERVAL == 0 and imgcnt < maximg:
                    x_t1 = nc.image_postprocessing(gray, IMAGE_SIZE_Y, IMAGE_SIZE_X, True, t)
                else:
                    x_t1 = nc.image_postprocessing(gray, IMAGE_SIZE_Y, IMAGE_SIZE_X, False, t)
            
            # store color image for video creation (we better get a lot of points in the presentation!)
            if feedback:
                nc.store_img(nc.getColor(game_state), nc.get_t(t), feedback_path + "/forVideo")
            
            # add image to the state
            s_t1 = nc.update_state(s_t, x_t1)
            
            # store the transition in D
            D.append((s_t, a_t, r_t, s_t1, terminal))
            if len(D) > REPLAY_MEMORY:
                D.popleft()
                
            # update old values
            old_health = new_health
            
        # after action(s) are executed start the training
        if t > observe and not evaluate:
            if t == observe+1:
                print("Observing done")
            
            # sample a minibatch to train on
            minibatch = random.sample(D, BATCH)

            # get the batch variables
            s_batch   = [d[0] for d in minibatch]
            a_batch   = [d[1] for d in minibatch]
            r_batch   = [d[2] for d in minibatch]
            s1_batch  = [d[3] for d in minibatch]
            
            # feed our network with the future state and predict the Q-values
            predictedQ_batch = readout.eval(feed_dict = {s : s1_batch})
            
            # target variable in cost function
            y_batch = []
            
            # calculate y for all transitions in the minibatch
            for i in range(0, len(minibatch)):
                # if terminal only equals reward
                if minibatch[i][4]:
                    y_batch.append(r_batch[i])
                else:
                    y_batch.append(r_batch[i] + GAMMA * np.max(predictedQ_batch[i]))
                    
            # perform gradient step
            train_step.run(feed_dict = {
                y : y_batch,
                a : a_batch,
                s : s_batch})
        
        
        if feedback:
            
            # store an image for feedback if amximum amount not yet reached
            if t % IMG_STORED_INTERVAL == 0 and imgcnt < maximg:
                #nc.store_img(x_t1, str(t), feedback_path)
                imgcnt += 1
                
                #and store the corresponding q-values
                qfile = open(qfile_path, 'a')
                qfile.write(str(t) + ": Q-Values:" + str(readout_t) + "\n")
                qfile.close() 
        
        # save progress every x iterations
        if not evaluate:
            if t % STORE == 0:
                saver.save(sess, store_path + '/' + GAME + '-dqn', global_step = t)
                
                current_time = time.time() - start_time
                
                reward_p_turn = reward_all / (t-t_last_save)
                
                reward_file = open(reward_path, 'a')
                reward_file.write(str(t) + ":\n reward " + str(round(reward_p_turn, 4)) + ", time " + str(round(current_time, 4)) + ", crates " + str(round(crate_counter, 4)) + "\n")
                reward_file.close() 
                
                print("Saved weights after", t, "steps")
                
                # reset paramters
                t_last_save = t
                reward_all = 0
                crate_counter = 0
                
		# if in evaluation mode store in a different interval
        else:
            if t % REWARD_LOG_EVALUATE == 0:
                current_time = time.time() - start_time
                reward_p_turn = reward_all / (t-t_last_save)
                reward_file = open(reward_path, 'a')
                reward_file.write("Evaluation_" + str(t) + ":\n reward " + str(round(reward_p_turn, 4)) + ", time " + str(round(current_time, 4)) + ", crates " + str(round(crate_counter, 4)) + "\n")
                reward_file.close()
                
                
                t_last_save = t
                reward_all = 0
                crate_counter = 0
        
        # end the program if final step reached
        if t == end:

            reward_file = open(reward_path, 'a')
            reward_file.write("-- Network terminated --\n")
            reward_file.close()    
            
            reward_p_turn = reward_all / (t-t_last_save)
            
            print("Network reached final step", end)
            print("Reward per step:", reward_p_turn)
            print("Crates overall:", crate_counter)
            print("************************* Done *************************")
            break
        
        # update the old values
        s_t = s_t1
        t += 1
             
    game.close()
      

def main():

    # is this flag set, the game will not store any weights and
    # will only play for a few rounds
    # information will be stored how successful the network is
    EVALUATE = True
    
    # is this flag set, the game will store a lot of information in
    # additional files and on the console
    # also a lot of images will be stored
    FEEDBACK = False
    
    # the images stacked together
    stack = int(sys.argv[1])
    
    # the amount of frames an action is repeated until a new one is selected
    frame_action = int(sys.argv[2])
    
    # the amount of actions until epsilon reaches his final value
    explore_anneal = int(sys.argv[3])
    
    # if the depth image is added to the normal grayscale image
    with_depth = sys.argv[4]
    
    if with_depth == "1":
        with_depth = True
    else:
        with_depth = False
        
    if EVALUATE:
        print("Testing results from network with following parameters:")
        print("Stack:", stack, "Frame/Action:", frame_action, "Depth:", with_depth)
    else:
        print("Executing network with following parameters:")
        print("Images stacked together:", stack)
        print("New action will be taken every", frame_action, "frame")
        print("Randomization factor will anneal to", FINAL_EPSILON*100, "% over", explore_anneal, "steps")
        print("Adding depth image:", with_depth)  
        print("Network will observe for", OBSERVE, "steps before calibrating")
        print("Weights will be saved every", STORE, "steps")
        print("Network will calibrate for a maximum of", END, "steps")
    
    actions, num_actions, game = initgame(EVALUATE)
    sess = tf.InteractiveSession()
    s, readout, h_fc1 = createNetwork(num_actions, stack, IMAGE_SIZE_Y/2, IMAGE_SIZE_X, KERNEL1, STRIDE1, KERNEL2, STRIDE2, KERNEL3, STRIDE3)
    trainNetwork(actions, num_actions, game, s, readout, h_fc1, sess, stack, frame_action, explore_anneal, with_depth, EVALUATE, FEEDBACK)
    
if __name__ == "__main__":
    main()
