import numpy as np
import cPickle as pickle
import keras.models
import sklearn.neighbors
import sklearn.externals
import pianoroll_utils
import h5py

class UnitPredictor:
    def __init__(self):
        # Other properties
        self.NUM_PITCHES = 128
        self.NUM_TICKS = 96
        return

    def get_comp_pianoroll(self, input_pianoroll):
        """
        Placeholder function, currently returns the same input.
        Should override in future classes to return a new pianoroll.
        """
        return input_pianoroll

class UnitSelector(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        KNN_MODEL_FILE = "./pickle_jar/unit_selector_knn.pkl"
        ENCODER_MODEL_FILE = "./models/encoder_v2_input_input.h5"
        # Load up the kNN model along with the units used to learn the model
        self.units = {}
        self.knn_model, self.units["input"], self.units["comp"] = sklearn.externals.joblib.load(KNN_MODEL_FILE)
        # Load up the encoder model
        self.encoder = keras.models.load_model(ENCODER_MODEL_FILE)
        return
    
    def get_flattened_encodings(self, inputs, encoder):
        """
        Given an input matrix of shape (M, 128, 96, 1) and a trained encoder model,
        run each M pianorolls through the encoder and return an (M, F) matrix 
        where F is the length of the FLATTENED embedding layer.
        """
        assert inputs.shape[1] == self.NUM_PITCHES
        assert inputs.shape[2] == self.NUM_TICKS
        assert inputs.shape[3] == 1
        
        encodings = encoder.predict(inputs)
        flat_encodings = encodings.reshape(encodings.shape[0], -1)
        return flat_encodings

    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        # Normalize input_pianoroll
        input_pianoroll = input_pianoroll / 127.
        # Get encoding of the input
        input_pianoroll = input_pianoroll.reshape(1, 128, 96, 1)
        input_encoding = self.get_flattened_encodings(input_pianoroll, self.encoder)
        # Prediction
        knn_index = self.knn_model.kneighbors(input_encoding, return_distance = False)[0][0]
        # Retrieve pianoroll
        comp_pianoroll = self.units["input"][knn_index].reshape(self.NUM_PITCHES, self.NUM_TICKS) * 127
        return comp_pianoroll

class UnitSelectorV2(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        self.MIN_PITCH = 13
        self.MAX_PITCH = 108
        self.NUM_PITCHES = self.MAX_PITCH - self.MIN_PITCH + 1
        # Load up the kNN model along with the units used to learn the model
        KNN_MODEL_FILE = "./models/vae_v7_unit_selector_knn.pkl"
        self.knn_model, UNITS_FILE = sklearn.externals.joblib.load(KNN_MODEL_FILE)
        f = h5py.File(UNITS_FILE, 'r')
        self.units = f['units_train']
        # Load up the encoder model
        ENCODER_MODEL_FILE = "./models/vae_v7_encoder.h5"
        self.encoder = keras.models.load_model(ENCODER_MODEL_FILE)
        return

    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        # Get input_pianoroll into the right shape
        input_pianoroll = pianoroll_utils.crop_pianoroll(input_pianoroll, self.MIN_PITCH, self.MAX_PITCH)
        # Get encoding of the input
        input_pianoroll = input_pianoroll[np.newaxis, ..., np.newaxis]
        input_encoding = self.encoder.predict(input_pianoroll)
        # Retrieve closest neighbor
        knn_index = self.knn_model.kneighbors(input_encoding, return_distance = False)[0][0]
        knn_pianoroll = self.units[knn_index].squeeze()
        # Pad the pianoroll from 88 to 128 keys
        knn_pianoroll = pianoroll_utils.pad_pianoroll(knn_pianoroll, self.MIN_PITCH, self.MAX_PITCH)
        return knn_pianoroll

class UnitAutoencoder(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        AUTOENCODER_MODEL_FILE = "./models/autoencoder_v4_input_comp.h5"
        # Load up the autoencoder model
        self.autoencoder = keras.models.load_model(AUTOENCODER_MODEL_FILE)
        return

    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        # Normalize input_pianoroll
        input_pianoroll = input_pianoroll / 127.
        # Get encoding of the input
        input_pianoroll = input_pianoroll.reshape(1, self.NUM_PITCHES, self.NUM_TICKS, 1)
        autoencoder_output = self.autoencoder.predict(input_pianoroll) # (1, 128, 96, 1)
        output_pianoroll = autoencoder_output[0].reshape(self.NUM_PITCHES, self.NUM_TICKS) * 127
        # Quantize the output
        output_pianoroll[output_pianoroll < 10] = 0
        output_pianoroll[output_pianoroll > 0] = 100
        return output_pianoroll

class UnitVariationalAutoencoder(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        ENCODER_MODEL_FILE = "./models/vae_v1_encoder.h5"
        DECODER_MODEL_FILE = "./models/vae_v1_generator.h5"
        # Load up the autoencoder model
        latent_dim = 2400
        epsilon_std = 1.0

        self.encoder = keras.models.load_model(ENCODER_MODEL_FILE,
            custom_objects={'latent_dim': latent_dim, 
                            'epsilon_std': epsilon_std})
        self.decoder = keras.models.load_model(DECODER_MODEL_FILE,
            custom_objects={'latent_dim': latent_dim, 
                            'epsilon_std': epsilon_std})
        return
    
    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        # Normalize input_pianoroll
        input_pianoroll = input_pianoroll / 127.
        # Get encoding of the input
        input_pianoroll = input_pianoroll.reshape(1, self.NUM_PITCHES, self.NUM_TICKS, 1)
        # autoencoder_output = self.encoder.predict(input_pianoroll) # (1, 128, 96, 1)
        z = self.encoder.predict(input_pianoroll)
        autoencoder_output = self.decoder.predict(z)

        output_pianoroll = autoencoder_output[0].reshape(self.NUM_PITCHES, self.NUM_TICKS) * 127
        # Quantize the output
        output_pianoroll[output_pianoroll < 10] = 0
        output_pianoroll = np.clip(output_pianoroll * 2, 0, 127)
        return output_pianoroll

class UnitVariationalAutoencoderOnsets(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        self.MIN_PITCH = 13
        self.MAX_PITCH = 108
        self.NUM_PITCHES = self.MAX_PITCH - self.MIN_PITCH + 1
        ENCODER_MODEL_FILE = "./models/vae_v9_encoder_latent50.h5"
        DECODER_MODEL_FILE = "./models/vae_v9_decoder_latent50.h5"
        # Load up the autoencoder model
        latent_dim = 50
        epsilon_std = 1.0

        self.encoder = keras.models.load_model(ENCODER_MODEL_FILE,
            custom_objects={'latent_dim': latent_dim, 
                            'epsilon_std': epsilon_std})
        self.encoder._make_predict_function()
        # https://github.com/keras-team/keras/issues/6462
        self.decoder = keras.models.load_model(DECODER_MODEL_FILE,
            custom_objects={'latent_dim': latent_dim, 
                            'epsilon_std': epsilon_std})
        self.decoder._make_predict_function()
        # https://github.com/keras-team/keras/issues/6462
        return
    
    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        assert input_pianoroll.shape[0] == 128
        assert input_pianoroll.shape[1] == 96
        assert np.max(input_pianoroll) <= 1.0

        # Get binarized onsets
        input_pianoroll = np.pad(input_pianoroll, ((0,0),(1,0)), 'constant')
        input_pianoroll = input_pianoroll[:,1:] - input_pianoroll[:,:-1]
        input_pianoroll = (input_pianoroll > 0.1).astype('float16')
        # Crop / reshape to suit model
        input_pianoroll = pianoroll_utils.crop_pianoroll(input_pianoroll, self.MIN_PITCH, self.MAX_PITCH)
        input_pianoroll = input_pianoroll.reshape(1, self.NUM_PITCHES, self.NUM_TICKS, 1)
        # Encode and decode
        z = self.encoder.predict(input_pianoroll)
        autoencoder_output = self.decoder.predict(z)
        # Pad / reshape to original shape
        output_pianoroll = autoencoder_output.squeeze()
        output_pianoroll = pianoroll_utils.pad_pianoroll(output_pianoroll, self.MIN_PITCH, self.MAX_PITCH)
        # Preprocess (binarize)
        output_pianoroll = pianoroll_utils.pianoroll_preprocess(output_pianoroll, is_onsets_matrix=True)
        return output_pianoroll

class UnitAccompanier(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        # Music shape
        self.MIN_PITCH = 21 # A-1 (MIDI 21)
        self.MAX_PITCH = 108 # C7 (MIDI 108)
        self.NUM_PITCHES = self.MAX_PITCH - self.MIN_PITCH + 1
        # Load up all our Keras models
        latent_dim = 10
        epsilon_std = 1.0
        ENCODER_MODEL_FILE = './models/vae_v4_encoder.h5'
        DECODER_MODEL_FILE = './models/vae_v4_generator.h5'
        RNN_MODEL_FILE = './models/rlstm_v3.h5'
        self.encoder = keras.models.load_model(ENCODER_MODEL_FILE, 
            custom_objects={'latent_dim': latent_dim, 'epsilon_std': epsilon_std})
        self.decoder = keras.models.load_model(DECODER_MODEL_FILE, 
            custom_objects={'latent_dim': latent_dim, 'epsilon_std': epsilon_std})
        self.rnn = keras.models.load_model(RNN_MODEL_FILE)
        # Prepare the fixed memory
        self.WINDOW_LENGTH = 4
        self.x_input_embed = np.zeros((self.WINDOW_LENGTH, latent_dim))
        self.x_comp_embed = np.zeros((self.WINDOW_LENGTH, latent_dim))
        return

    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        # Normalize input_pianoroll
        input_pianoroll = input_pianoroll / 127.
        # Resize input_pianoroll from 128 to 88 keys
        input_pianoroll = pianoroll_utils.crop_pianoroll(input_pianoroll.T,
            self.MIN_PITCH, self.MAX_PITCH).T

        # Get encoding of the input
        input_pianoroll = input_pianoroll.reshape(1, self.NUM_PITCHES, self.NUM_TICKS, 1)
        input_embed = self.encoder.predict(input_pianoroll) # (1, 10)
        assert(input_embed.shape == (1, 10))
        # Append new input to past-inputs window
        self.x_input_embed = np.concatenate([self.x_input_embed[1:], input_embed], axis=0)
        assert(self.x_input_embed.shape == (self.WINDOW_LENGTH, 10))
        
        # Get prediction of next comp embedding
        next_comp_embed = self.rnn.predict([np.array([self.x_input_embed]), # (1, 10)
                                            np.array([self.x_comp_embed]) ])
        assert(next_comp_embed.shape == (1, 10))
        
        # Decode next comp embedding
        next_comp = self.decoder.predict(next_comp_embed) # (1, NUM_PITCHES, NUM_TICKS, 1)
        output_pianoroll = next_comp[0].reshape(self.NUM_PITCHES, self.NUM_TICKS) * 127
        # Quantize the output
        output_pianoroll[output_pianoroll < 10] = 0
        output_pianoroll[output_pianoroll > 0] = 100
        # Pad the pianoroll from 88 to 128 keys
        output_pianoroll = pianoroll_utils.pad_pianoroll(output_pianoroll.T,
            self.MIN_PITCH, self.MAX_PITCH).T

        # Append new comp to past-comps window
        self.x_comp_embed = np.concatenate([self.x_comp_embed[1:], next_comp_embed], axis=0)
        assert(self.x_comp_embed.shape == (self.WINDOW_LENGTH, 10))
        return output_pianoroll

class UnitAccompanierMono(UnitPredictor):
    def __init__(self):
        UnitPredictor.__init__(self)
        # Music shape
        self.MIN_PITCH = 13 # C-2 (MIDI 13)
        self.MAX_PITCH = 108 # C7 (MIDI 108)
        self.NUM_PITCHES = self.MAX_PITCH - self.MIN_PITCH + 1
        # Load up all our Keras models
        ENCODER_MODEL_FILE = './models/end2end_RNNdecoder_v1_encoder.h5'
        DECODER_MODEL_FILE = './models/end2end_RNNdecoder_v1_decoder.h5'
        self.encoder = keras.models.load_model(ENCODER_MODEL_FILE)
        self.encoder._make_predict_function() # https://github.com/keras-team/keras/issues/6462
        self.decoder = keras.models.load_model(DECODER_MODEL_FILE)
        self.decoder._make_predict_function() # https://github.com/keras-team/keras/issues/6462
        # Prepare the fixed memory
        self.WINDOW_LENGTH = 4
        self.x_input = np.zeros((self.WINDOW_LENGTH, self.NUM_PITCHES, self.NUM_TICKS, 1))
        self.x_comp = np.zeros((self.WINDOW_LENGTH, self.NUM_PITCHES, self.NUM_TICKS, 1))
        return

    def get_comp_pianoroll(self, input_pianoroll):
        """
        Given a input pianoroll with shape [NUM_PITCHES, NUM_TICKS],
        return an accompanying pianoroll with equivalent shape.
        """
        # Resize input_pianoroll from 128 to 96 keys
        input_pianoroll = pianoroll_utils.crop_pianoroll(input_pianoroll, self.MIN_PITCH, self.MAX_PITCH)

        # Get encoding of the input
        input_pianoroll = input_pianoroll[np.newaxis, ..., np.newaxis]
        assert(input_pianoroll.shape == (1, self.NUM_PITCHES, self.NUM_TICKS, 1))
        # Append new input to past-inputs window
        self.x_input = np.concatenate([self.x_input[1:], input_pianoroll], axis=0)
        assert(self.x_input.shape == (self.WINDOW_LENGTH, self.NUM_PITCHES, self.NUM_TICKS, 1))
        
        # Get prediction of next comp embedding
        next_comp = self.decode_sequence([np.array([self.x_input]), np.array([self.x_comp]) ])
        assert(next_comp.shape == (self.NUM_PITCHES, self.NUM_TICKS))
        
        # Pad the pianoroll to 128 keys
        output_pianoroll = pianoroll_utils.pad_pianoroll(next_comp, self.MIN_PITCH, self.MAX_PITCH)

        # Append new comp to past-comps window
        next_comp = next_comp[np.newaxis, ..., np.newaxis]
        self.x_comp = np.concatenate([self.x_comp[1:], next_comp], axis=0)
        assert(self.x_comp.shape == (self.WINDOW_LENGTH, self.NUM_PITCHES, self.NUM_TICKS, 1))
        return output_pianoroll

    def decode_sequence(self, input_seq_pair):
        num_decoder_tokens = self.NUM_PITCHES
        
        # Encode the input as state vectors.
        states_value = self.encoder.predict(input_seq_pair)

        # Generate empty target sequence of length 1.
        target_seq = np.zeros((1, 1, num_decoder_tokens))

        # Populate the first character of target sequence with the start token.
        start_token = np.zeros(num_decoder_tokens)
        start_token[-1] = 1 # Start token is [...,0,0,0,1]
        target_seq[0, 0, :] = start_token

        # Sampling loop for a batch of sequences
        # (to simplify, here we assume a batch of size 1).
        output_onehotmatrix = np.zeros((self.NUM_TICKS, num_decoder_tokens))
        output_onehotmatrix[0] = start_token
        for i in range(1,self.NUM_TICKS):
            output_tokens, h, c = self.decoder.predict(
                [target_seq] + states_value)

            # Sample a token
            sampled_token_index = np.argmax(output_tokens[0, -1, :])
            sampled_token = np.zeros(num_decoder_tokens)
            sampled_token[sampled_token_index] = 1 # One hot encoding
            # Write to output
            output_onehotmatrix[i] = sampled_token

            # Update the target sequence (of length 1).
            target_seq = np.zeros((1, 1, num_decoder_tokens))
            target_seq[0, 0, sampled_token_index] = 1.

            # Update states
            states_value = [h, c]

        assert np.all(np.sum(output_onehotmatrix, axis=1) == 1) # Each tick is a one-hot encoded vector
        output_pianoroll = pianoroll_utils.one_hot_to_pianoroll(output_onehotmatrix) 
        assert output_pianoroll.shape == (self.NUM_PITCHES, self.NUM_TICKS)
        return output_pianoroll