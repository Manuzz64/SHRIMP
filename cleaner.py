from sense_hat import SenseHat
from time import sleep

sense = SenseHat()
sense.set_rotation(270)

r = (255, 0, 6)
b = (0, 0, 255)
g = (0, 255, 0)
w = (255, 255, 255)
y = (255, 255, 0)
n = (0, 0, 0)

one_pixels = [
    n, n, n, n, n, n, n, n,
    n, n, n, n, n, n, n, n,
    n, n, n, n, n, n, n, n,
    n, n, n, r, r, n, n, n,
    n, n, n, r, r, n, n, n,
    n, n, n, n, n, n, n, n,
    n, n, n, n, n, n, n, n,
    n, n, n, n, n, n, n, n,
]

two_pixels = [
    n, n, n, n, n, n, n, n,
    n, n, n, n, n, n, n, n,
    n, n, r, r, r, r, n, n,
    n, n, r, n, n, r, n, n,
    n, n, r, n, n, r, n, n,
    n, n, r, r, r, r, n, n,
    n, n, n, n, n, n, n, n,
    n, n, n, n, n, n, n, n,
]

three_pixels = [
    n, n, n, n, n, n, n, n,
    n, r, r, r, r, r, r, n,
    n, r, n, n, n, n, r, n,
    n, r, n, n, n, n, r, n,
    n, r, n, n, n, n, r, n,
    n, r, n, n, n, n, r, n,
    n, r, r, r, r, r, r, n,
    n, n, n, n, n, n, n, n,
]

four_pixels = [
    r, r, r, r, r, r, r, r,
    r, n, n, n, n, n, n, r,
    r, n, n, n, n, n, n, r,
    r, n, n, n, n, n, n, r,
    r, n, n, n, n, n, n, r,
    r, n, n, n, n, n, n, r,
    r, n, n, n, n, n, n, r,
    r, r, r, r, r, r, r, r,
]

sense.set_pixels(one_pixels)
sleep(0.05)
sense.set_pixels(two_pixels)
sleep(0.05)
sense.set_pixels(three_pixels)
sleep(0.05)
sense.set_pixels(four_pixels)
sleep(0.05)
sense.show_message("All clean!")
sleep(0.05)
sense.set_pixels(four_pixels)
sleep(0.05)
sense.set_pixels(three_pixels)
sleep(0.05)
sense.set_pixels(two_pixels)
sleep(0.05)
sense.set_pixels(one_pixels)
sleep(0.05)
sense.clear()