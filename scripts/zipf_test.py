# import numpy
import numpy as np
import matplotlib.pyplot as plt

# Using zipf() method
gfg = np.random.zipf(2, 5000)

plt.hist(gfg, bins = 50, density = True)
plt.show()
