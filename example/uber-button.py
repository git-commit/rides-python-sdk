# Copyright (c) 2017 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Use an UberRidesClient to request and complete a ride.

This example demonstrates how to use an UberRidesClient to request a ride
under surge. After successfully requesting a ride, it updates the
ride status to 'completed' and deactivates surge.

To run this example:

    (1) Run `python authorize_rider.py` to get OAuth 2.0 Credentials
    (2) Run `python request_ride.py`
    (3) The UberRidesClient will make API calls and print the
        results to your terminal.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import time
from collections import namedtuple

try:
    from urllib.parse import parse_qs
    from urllib.parse import urlparse
except ImportError:
    from urlparse import parse_qs
    from urlparse import urlparse

from builtins import input

from example.utils import create_uber_client
from example.utils import fail_print
from example.utils import import_oauth2_credentials
from example.utils import paragraph_print
from example.utils import success_print

from uber_rides.errors import ClientError
from uber_rides.errors import ServerError
from geopy.geocoders import Nominatim

from fcache.cache import FileCache

# Starting location
START_NAME = "Lichtenbergstraße 6, Garching bei München"

# End location
END_NAME = "Moosacher Straße 86, München"

# uber pool
UFP_PRODUCT_ID = '26546650-e557-4a7b-86e7-6a3942445247'
UFP_PRODUCT_ID = 'bcb6224a-f21e-4cde-8e08-53cf9c98164d'

# uber black
SURGE_PRODUCT_ID = 'd4abaae7-f4d6-4152-91cc-77523e8165a4'


def estimate_ride(api_client, start_lat, start_lng, end_lat, end_lng):
    """Use an UberRidesClient to fetch a ride estimate and print the results.

    Parameters
        api_client (UberRidesClient)
            An authorized UberRidesClient with 'request' scope.
    """
    try:
        estimate = api_client.estimate_ride(
            product_id=SURGE_PRODUCT_ID,
            start_latitude=start_lat,
            start_longitude=start_lng,
            end_latitude=end_lat,
            end_longitude=end_lng,
            seat_count=2
        )

    except (ClientError, ServerError) as error:
        fail_print(error)

    else:
        success_print(estimate.json)


def update_ride(api_client, ride_status, ride_id, verbose=True):
    """Use an UberRidesClient to update ride status and print the results.

    Parameters
        api_client (UberRidesClient)
            An authorized UberRidesClient with 'request' scope.
        ride_status (str)
            New ride status to update to.
        ride_id (str)
            Unique identifier for ride to update.
    """
    try:
        update_product = api_client.update_sandbox_ride(ride_id, ride_status)

    except (ClientError, ServerError) as error:
        fail_print(error)

    else:
        if verbose:
            message = '{} New status: {}'
            message = message.format(update_product.status_code, ride_status)
            success_print(message)

def request_ufp_ride(api_client, start_lat, start_lng, end_lat, end_lng):
    """Use an UberRidesClient to request a ride and print the results.

    Parameters
        api_client (UberRidesClient)
            An authorized UberRidesClient with 'request' scope.

    Returns
        The unique ID of the requested ride.
    """
    try:

        estimate = api_client.estimate_ride(
            product_id=UFP_PRODUCT_ID,
            start_latitude=start_lat,
            start_longitude=start_lng,
            end_latitude=end_lat,
            end_longitude=end_lng,
            seat_count=2
        )
        fare = estimate.json.get('fare')

        request = api_client.request_ride(
            product_id=UFP_PRODUCT_ID,
            start_latitude=start_lat,
            start_longitude=start_lng,
            end_latitude=end_lat,
            end_longitude=end_lng,
            seat_count=2,
            fare_id=fare['fare_id']
        )

    except (ClientError, ServerError) as error:
        print(error)
        fail_print(error)
        return

    else:
        #success_print(estimate.json)
        #success_print(request.json)

        fare = estimate.json["fare"]["display"]
        pickup_estimate = estimate.json["pickup_estimate"]
        trip_duration_estimate = estimate.json["trip"]["duration_estimate"] / 60
        paragraph_print("Die Fahrt wird vorraussichtlich %s kosten.\nDer Fahrer kann in %s Minuten da sein.\nDie Fahrdauer bis zum Ziel beträgt %s Minuten"
                        % (fare, pickup_estimate, trip_duration_estimate))

        return (request.json.get('request_id'), pickup_estimate, fare)


def get_ride_details(api_client, ride_id, verbose=True):
    """Use an UberRidesClient to get ride details and print the results.

    Parameters
        api_client (UberRidesClient)
            An authorized UberRidesClient with 'request' scope.
        ride_id (str)
            Unique ride identifier.
            :param verbose:
            :param verbose:
    """
    try:
        ride_details = api_client.get_ride_details(ride_id)

    except (ClientError, ServerError) as error:
        fail_print(error)

    else:
        if verbose:
            success_print(ride_details.json)
        return ride_details.json


def get_latlng(location):
    cache = FileCache('uber-button-cache')

    if location not in cache:
        geolocator = Nominatim(user_agent="Uber-Button")
        geolocator.timeout = 60
        time.sleep(1.1)
        cache[location] = geolocator.geocode(location)
        cache.sync()

    return cache[location]


def on_button(channel):
    """Run the example.

    Create an UberRidesClient from OAuth 2.0 Credentials, update a sandbox
    product's surge, request and complete a ride.
    """
    credentials = import_oauth2_credentials()
    api_client = create_uber_client(credentials)

    # ride request with upfront pricing flow
    api_client.cancel_current_ride()

    verbose = True

    print("Frage Koordinaten ab...")

    start = get_latlng(START_NAME)
    end = get_latlng(END_NAME)

    # Manually set coordinates
    #UberLocation = namedtuple('UberLocation', 'latitude longitude')
    #start = UberLocation(48, 11)
    #end = UberLocation(48, 10)

    if start is None:
        print("Bitte gültige Startadresse eingeben")
        return
    if end is None:
        print("Bitte gültige Endadresse eingeben")

    print("Start (%s, %s)" % (start.latitude, start.longitude))
    print("Ende (%s, %s)" % (end.latitude, end.longitude))

    #Request a ride with upfront pricing product
    paragraph_print("Anfrage einer Fahrt...\nVon: %s\nNach: %s" % (start, end))
    ride_id, pickup_estimate, fare = request_ufp_ride(api_client, start.latitude, start.longitude, end.latitude, end.longitude)

    paragraph_print("Akzeptiere Fahrt...")
    update_ride(api_client, 'accepted', ride_id, verbose=verbose)

    paragraph_print("Warten bis Fahrer da ist...")
    show_ui(pickup_estimate, fare)

    paragraph_print("Einsteigen und losfahren...")
    update_ride(api_client, 'in_progress', ride_id, verbose=verbose)
    time.sleep(5)

    paragraph_print("Am Ziel angekommen...")
    update_ride(api_client, 'completed', ride_id, verbose=verbose)


def init_gpio():
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
    GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)


def show_ui(eta, price):
    import PySimpleGUI as sg
    font = ("Helvetica", 50)
    layout = [[sg.Text('Ankunft in: %s Minuten' % eta, font=font)],
              [sg.Text('Preis: %s' % price, font=font)],
              [sg.OK(font=font)]]

    # Create the Window
    window = sg.Window('UberButton', layout)
    # Event Loop to process "events"
    while True:
        event, values = window.Read()
        print(event, values)
        if event in (None, 'OK'):
            break

    window.Close()


if __name__ == '__main__':
    try:
        import RPi.GPIO as GPIO
    except ImportError as e:
        print("Starte im Nicht-Raspberry-Pi Modus")
        on_button("")
    else:
        print("Starte im Raspberry-Pi Modus")
        init_gpio()
        GPIO.add_event_detect(10,GPIO.RISING, callback=on_button, bouncetime=2000) # Setup event on pin 10 rising edge
        message = input("Press enter to quit\n\n") # Run until someone presses enter
        GPIO.cleanup() # Clean up