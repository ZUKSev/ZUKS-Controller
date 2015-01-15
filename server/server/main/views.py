from server.main.models import Volunteer, VolunteerGroup, Location
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import detail_route
from server.main.serializers import VolunteerSerializer, LocationSerializer, VolunteerGroupSerializer
from server.main.event_bus import EventBus, EventBusLogger
from server.main.web_notifier import WebNotifier

default_event_bus = EventBus()
logger = EventBusLogger(default_event_bus)
web_notifier = WebNotifier(default_event_bus)

class EventViewSet(viewsets.ModelViewSet):
  '''
  ModelViewSet that fires events, when the model
  is changed. 

  The events are published to the global 
  default_event_bus.
  '''

  def create(self, request, *args, **kwargs):
    response = super().create(request, *args, **kwargs)
    self.fire_response('create', response)
    return response

  def update(self, request, *args, **kwargs):
    originalResponse = self.retrieve(request, request.data['id'])
    response = super().update(request, *args, **kwargs)
    self.fire_response('update', response, originalResponse.data)
    return response

  def destroy(self, request, *args, **kwargs):
    originalResponse = self.retrieve(request, request.data['id'])
    response = super().destroy(request, *args, **kwargs)
    self.fire_response('delete', response, originalResponse.data)
    return response

  def fire_response(self, event, response, original={}):
    '''
    Fires an event, based on the event name
    and a reponse object.

    The event is only fired, when the status_code
    of the response indicates that the request
    was successfully processed.

    As prefix for the event name the class variable
    event_key is used.

    Keyword arguments:
    event -- the event name, used to create the event_key
    response -- the reponse object
    original -- the data before the executed operation was applied
    '''
    if status.is_success(response.status_code):
      key = "%s_%s" % (self.__class__.event_key, event)
      self.fire(key, {'old': original, 'new': response.data})

  def fire(self, key, data): 
    '''
    Publishes a new event to the global 
    default_event_bus.

    Keyword arguments:
    key -- the event key
    data -- the data to publish
    '''
    default_event_bus(key, data)

class VolunteerViewSet(EventViewSet):
  """
  API endpoint for volunteers
  """
  queryset = Volunteer.objects.all()
  serializer_class = VolunteerSerializer
  event_key = "volunteer"

class LocationViewSet(EventViewSet):
  """
  API endpoint for locations
  """
  queryset = Location.objects.all()
  serializer_class = LocationSerializer
  event_key = "volunteer"

  def fire(self, key, data):
    '''
    Fires an volunteer dataset, when the location
    was changed.
    '''
    location = Location.objects.get(id=data['new']['id'])
    volunteer = location.volunteer
    volunteer_data = VolunteerSerializer(volunteer).data
    super().fire(key, volunteer_data)

class VolunteerGroupViewSet(EventViewSet):
  """
  API endpoint for volunteer groups
  """
  queryset = VolunteerGroup.objects.all()
  serializer_class = VolunteerGroupSerializer
  event_key = "volunteerGroup"

  @detail_route()
  def members(self, request, pk=None):
    volunteers = self.get_object().members.all()
    serializer = VolunteerSerializer(volunteers, many=True)
    return Response(serializer.data)
