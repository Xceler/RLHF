import os 
import torch as T 
import torch.nn as nn 
import torch.nn.functional as F 
import torch.optim as optim 
import numpy as np


class OUActionNoise(object):
    def __init__(self, mu, sigma =0.15, theta = .2, dt = 1e-2, x0 =None):
        self.theta = theta
        self.mu = mu 
        self.sigma = sigma 
        self.dt = dt 
        self.x0 = x0 
        self.reset()
    
    def __call__(self):
        x = self.x_prev + self.thteta *  (self.mu -self.x_prev) * self.dt + self.sigma * np.sqrt(self.dt) * np.random.normal(size = self.mu.shape)
        self.x_prev = x 
        return x
    
    def reset(self):
        self.x_prev  = self.x0 if self.x0 is not None else np.zeros_like(self.mu)
    

    def __repr__(self):
        return "ÖrnsteinUhlenbeckActionNoise(mu={}, sigma = {})".format(self.mu, self.sigma)


class ReplayBuffer(object):
    def __init__(self, max_size, input_shape, n_actions):
        self.mem_size = max_size 
        self.mem_cntr = 0
        self.state_memory = np.zeros((self.mem_size , *input_shape))
        self.new_state_memory = np.zeros((self.mem_size * input_shape))
        self.action_memory = np.zeros((self.mem_size, n_actions))
        self.reward_memory = np.zeros(self.mem_size)
        self.terminal_memory = np.zeros(self.mem_size, dtype= np.float32)


    def store_transition(self, state, action, reward, state_ , done):
        index = self.mem_cntr % self.mem_size 
        self.state_memory[index] =state 
        self.new_state_memory[index] = state_ 
        self.action_memory[index] = action 
        self.reward_memory[index] = reward 
        self.terminal_memory[index] = 1 - done 
        self.mem_cntr += 1 

    def sample_buffer(self, batch_size):
        max_mem = min(self.mem_cntr, self.mem_size)
        batch = np.random.choice(max_mem ,batch_size)
        states = self.state_memory[batch]
        actions = self.action_memory[batch]
        rewards = self.reward_memory[batch]
        states_ = self.new_state_memory[batch]
        terminal = self.terminal_memory[batch]

        return states, actions, rewards, states_, terminal 



class CriticNetwork(nn.Module):
    def __init__(self, beta, input_dims, fc1_dims, fc2_dims, n_actions, name, 
                 chkpt_dir = 'tmp/ddpg'):
        
        super(CriticNetwork, self).__init__() 
        self.input_dims = input_dims 
        self.fc1_dims = fc1_dims 
        self.fc2_dmis = fc2_dims 
        self.n_actions = n_actions 
        self.chekpoint_file = os.path.join(chkpt_dir , name +'_ddpg')
        self.fc1 = nn.Linear(*self.input_dims , self.fc1_dims)
        f1 = 1./np.sqrt(self.fc1.weight.data.size()[0])
        T.nn.init.uniform_(self.fc1.weight.data, -f1, f1)
        T.nn.init.uniform_(self.fc1.bias.data, -f1, f1)

        self.bn1 = nn.LayerNorm(self.fc1_dims)
        self.fc2  = nn.Linear(self.fc1_dims, self.fc2_dims)
        
        f2 =  1./np.sqrt(self.fc2.weight.data.size())[0]
        T.nn.init.uniform_(self.fc2.weight.data, -f2, f2) 
        T.nn.init.uniform_(self.fc2.bias.data, -f2, f2)

        self.bn2 = nn.LayerNorm(self.fc2_dims)

        self.action_value = nn.Linear(self.n_actions, self.fc2_dims)
        f3 = 0.003 
        self.q = nn.Linear(self.fc2_dims , 1)
        T.nn.init.uniform_(self.q.weight.data, -f3, f3)
        T.nn.init.uniform_(self.q.bias.data, -f3, f3)

        self.optimizer = optim.Adam(self.parameters(),lr= beta)
        self.device = T.device('cuda: 0' if T.cuda.is_available() else "cuda:1")

        self.to(self.device)
    

    def forward(self, state, action):
        state_value = self.fc1(state) 
        state_value = self.bn1(state_value) 
        state_value = F.relu(state_value) 
        state_value = self.fc2(state_value) 
        state_value = self.bn2(state_value) 

        action_value = F.relu(self.action_value(action))
        state_action_value = F.relu(T.add(state_value, action_value))
        state_action_value = self.q(state_action_value)
    
    def save_checkpoint(self):
        print("....Saving Checkpoint....")
        T.save(self.state_dict(), self.checkpoint_file)
    

    def load_checkpoint(self):
        print("....Loading Checkpoint........")
        self.load_state_dict(T.load(self.checkpoint_file))

    

class ActorNetwork(nn.Module):
    def __init__(self, alpha, input_dims , fc1_dims , fc2_dims , n_actions, name, 
                 chkpt_dir = "tmp/ddpg"):
        

        super(ActorNetwork, self).__init__() 
        self.input_dims = input_dims 
        self.fc1_dims = fc1_dims 
        self.fc2_dims = fc2_dims 
        self.n_actions = n_actions 
        self.checkpoint_file = os.path.join(chkpt_dir, name+ '_ddpg')

        self.fc1  = nn.Linear(*self.input_dims , self.fc1_dims)
        f1 = 1./np.sqrt(self.fc1.weight.data.size()[0])
        T.nn.init.uniform_(self.fc1.weight.data, -f1 , f1) 
        T.nn.init.uniform_(self.fc1.bias.data, -f1, f1)

        self.bn1 = nn.LayerNorm(self.fc1_dims)
        self.fc2 = nn.Linear(self.fc1_dims, self.fc2_dims)

        f2 = 1./np.sqrt(self.fc2.weight.data.size())[0]
        T.nn.init.uniform_(self.fc2.weight.data, -f2, f2)
        T.nn.init.uniform_(self.fc2.bias.data, -f2, f2)

        self.bn2 = nn.LayerNorm(self.fc2_dims) 

        f3  = 0.003 

        self.mu = nn.Linear(self.fc2_dims , self.n_actions)
        T.nn.init.uniform_(self.mu.weight.data, -f3, f3) 
        T.nn.init.uniform_(self.mu.bias.data, -f3, f3) 

        self.optimizer  = optim.Adam(self.parameters(), lr = alpha)
        self.device = T.device('cuda:0' if T.cuda.is_available() else "cuda:1")

        self.to(self.device) 
    

    def forward(self, state):
        x = self.fc1(state) 
        x = self.bn1(x) 
        x = F.relu(x) 
        x =self.fc2(x) 
        x = self.bn2(x) 
        x = F.relu(x) 
        x = T.tanh(self.mu(x)) 

        return x 
    
    def save_checkpoint(self):
        print("....saving checkpoint....")
        T.save(self.state_dict(), self.checkpoint_file) 
    

    def load_checkpoint(self):
        print("....Loading Checkpoint....")
        self.load_state_dict(T.load(self.checkpoint_file))

