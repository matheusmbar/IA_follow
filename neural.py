

import numpy as np

def random_gain ():
#    return np.random.rand() *10 - 5
#    return np.random.rand()*2 - 1
    return np.random.normal()

class neuron :
    def __init__(self, n_inputs, gains):
        #count bias value as a required gain value
        self.required_gains = n_inputs + 1
        if self.required_gains != len(gains):
            raise Exception ("Incorrect amount of gain values provided. {}!={}".format(self.required_gains,len(gains)))
        self.n_inputs = n_inputs
        self.gains = list(gains)
        self.out_func = self.default_out_func

        # print(gains)

    def default_out_func(self,value):
        #rectifier
        return max(0, value)

    def evaluate (self, inputs):
        if len(inputs) < self.n_inputs:
            raise Exception ("Incorrect amount of inputs provided. {}!={}".format(self.n_inputs,len(inputs)))
        sum = 0
        for i in range(self.n_inputs):
            sum += self.gains[i] * inputs[i]
        #sum the bias
        sum += self.gains[-1]
        # print ("neuron result:", sum)
        return self.out_func(sum)

    def get_gains (self):
        return self.gains

    def set_gains (self,new_gains):
        self.gains = list(new_gains[:self.required_gains])
        # print (self.gains)
        return list(new_gains[self.required_gains:])

class layer:
    def __init__(self, n_inputs, n_neurons, gains=None):
        #add an additional required gain to act as bias on each neuron
        self.required_gains = n_neurons * (n_inputs + 1)
        self.n_neurons = n_neurons
        self.n_inputs = n_inputs
        #print ("Create a layer with {} inputs and {} outputs".format (self.n_inputs, self.n_neurons))
        if gains == None:
            gains = list()
            for g in range(self.required_gains):
                #gains.append(np.random.normal()) 
                gains.append(random_gain()) 
                # gains.append(g)
        else:
            if len(gains) < self.required_gains:
                raise Exception ("Incorrect amount of gain values provided. {}!={}".format(len(gains),self.required_gains))
        self.gains = list(gains)
        self.neurons = list()
        for i in range(self.n_neurons):
            self.neurons.append(neuron(self.n_inputs, gains[i*(self.n_inputs+1):(i+1)*(self.n_inputs+1)]))

    def evaluate (self, inputs):
        out = list()
        for n in self.neurons:
            out.append(n.evaluate(inputs))
        return out

    def set_gains (self, new_gains):
        for n in self.neurons:
            new_gains = n.set_gains(new_gains)
        return new_gains

    def get_gains (self):
        gains = list()
        for n in self.neurons:
            gains += n.get_gains()
        self.gains = gains
        return gains

class network:
    def __init__ (self, n_inputs, layers_setup, gains=None):
        self.n_inputs = n_inputs
        self.layers_setup = layers_setup
        self.n_layers = len(layers_setup)
        self.gains = gains
        self.required_gains = 0
        inputs = n_inputs
        for l in layers_setup:
            self.required_gains += (inputs + 1) * l
            inputs = int(l)
        #print ("{} gains required for this network".format(self.required_gains))

        self.layers = list()

        gains_used = 0
        inputs = self.n_inputs

        for i in range(self.n_layers):
            outputs = self.layers_setup[i]
            if self.gains==None:
                gains = None
            else:
                gains = self.gains[gains_used:gains_used + (inputs + 1)*outputs]
                gains_used += (inputs + 1)*outputs
            self.layers.append(layer(inputs, outputs, gains=gains))
            inputs = outputs

    def evaluate (self, inputs):
        in_values = list(inputs)

        for i in range (self.n_layers):
            out = self.layers[i].evaluate(in_values)
            in_values = list(out)
        return out

    def set_gains (self, new_gains):
        if (new_gains == None):
            new_gains = list()
            for i in range(self.required_gains):
                new_gains.append(random_gain())
        for l in self.layers:
            new_gains = list(l.set_gains(new_gains))
        return new_gains

    def get_gains (self):
        #print ("set network gains")
        gains = list()
        for l in self.layers:
            gains += l.get_gains()
        self.gains = gains
        return gains
    
def mutation (gains):
    gains_len = len(gains)
    gains_to_mutate = int(np.random.rand() * gains_len * 1) 
    
    mutated = 0

    while mutated < gains_to_mutate:
        mutated += 1
        gain_pos = int(np.random.rand()*gains_len)
        mutate_type =  round(np.random.rand() * 3)
        if mutate_type == 0:   #set a new random value
            gains[gain_pos] = random_gain()
        elif mutate_type == 1: #random multiply
            # gains[gain_pos] *= (1+ 0.1*random_gain())
            gains[gain_pos] *= random_gain()
        else:   #random sum
            # gains[gain_pos] += 0.1*random_gain()
            gains[gain_pos] += random_gain()
    # print ("Mutated:", mutated)
    return gains

def mutation2 (gains):
    gains_len = len(gains)
    gains_to_mutate = int(np.random.rand() * gains_len * 1) 
    
    mutated = 0

    while mutated < gains_to_mutate:
        mutated += 1
        gain_pos = int(np.random.rand()*gains_len)
        gains[gain_pos] = random_gain()
    # print ("Mutated:", mutated)
    return gains
    


if __name__ == "__main__":
#    n = network (10,[4])
#    print("\t\tFinal result:", n.evaluate([1,1,1,1]))

#    inputs = [np.random.normal(),np.random.normal(),np.random.normal(),np.random.normal()]
    exit()