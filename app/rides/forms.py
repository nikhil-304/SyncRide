from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, DateTimeField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class OfferRideForm(FlaskForm):
    start_location = StringField('Start Location', validators=[DataRequired()])
    end_location = StringField('End Location', validators=[DataRequired()])
    start_latitude = FloatField('Start Latitude', validators=[DataRequired()])
    start_longitude = FloatField('Start Longitude', validators=[DataRequired()])
    end_latitude = FloatField('End Latitude', validators=[DataRequired()])
    end_longitude = FloatField('End Longitude', validators=[DataRequired()])
    departure_time = DateTimeField('Departure Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    available_seats = IntegerField('Available Seats', validators=[DataRequired(), NumberRange(min=1, max=4)])
    price = FloatField('Price per Seat', validators=[DataRequired(), NumberRange(min=0)])
    vehicle_type = StringField('Vehicle Type', validators=[DataRequired()])
    vehicle_number = StringField('Vehicle Number', validators=[DataRequired()])
    submit = SubmitField('Offer Ride')

class FindRideForm(FlaskForm):
    pickup_latitude = HiddenField('Pickup Latitude')
    pickup_longitude = HiddenField('Pickup Longitude')

class RequestRideForm(FlaskForm):
    pickup_location = StringField('Pickup Location', validators=[DataRequired()])
    pickup_latitude = FloatField('Pickup Latitude', validators=[DataRequired()])
    pickup_longitude = FloatField('Pickup Longitude', validators=[DataRequired()])
    seats_requested = IntegerField('Number of Seats', validators=[DataRequired(), NumberRange(min=1, max=4)])
    submit = SubmitField('Request Ride')

class RatingForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = StringField('Comment', validators=[Length(max=500)])
    submit = SubmitField('Submit Rating')
