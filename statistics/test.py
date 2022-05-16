import matplotlib.pyplot as plt
import numpy as np

plt.gcf().clear()
x = np.arange(-2*np.pi, 2*np.pi, 0.1)
fig = plt.figure(1)
ax = fig.add_subplot(111)
ax.plot(x, np.sin(x), label='Sine')
ax.plot(x, np.cos(x), label='Cosine')
ax.plot(x, np.arctan(x), label='Inverse tan')
handles, labels = ax.get_legend_handles_labels()
lgd = ax.legend(handles, labels, loc='center left', bbox_to_anchor=(0.5,-0.2))
text = ax.text(-0.2,1.05, "Aribitrary text", transform=ax.transAxes)
ax.set_title("Trigonometry")
ax.grid('on')
fig.savefig('samplefigure', bbox_extra_artists=(lgd,text), bbox_inches='tight')
