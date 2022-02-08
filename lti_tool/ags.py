from datetime import datetime
from pytz import utc

from urllib.parse import urlsplit, urlunsplit


def ts2str(ts):
    """Generates LTI conformant date-time string.

    :param ts: datetime object
    :rtype: date-time (utc) string in ISO 8601 representation with
        millisecond precision
    """
    return ts.astimezone(utc).isoformat(timespec='milliseconds')


class LineItemManager:
    def __init__(self, context, client):
        self.context = context
        self._client = client

    def _build_url(self, url, affix):
        url_parts = urlsplit(url)
        return urlunsplit((
            url_parts.scheme,
            url_parts.netloc,
            f'{url_parts.path}{affix}',
            url_parts.query,
            url_parts.fragment
        ))

    def get(self, lineitem_id):
        """Gets a lineitem.

        :param lineitem_id: ID (url) of the lineitem
        :rtype: :class:`ags.LineItem`
        """
        headers = {
            'Accept': 'application/vnd.ims.lis.v2.lineitem+json'
        }

        resp = self._client.get(
            lineitem_id,
            context=self.context,
            headers=headers
        ).json()

        return LineItem(self, resp, loaded=True)

    def create(self, label='', score_maximum=100, resource_link_id=None,
               resource_id=None, tag=None, start_ts=None, end_ts=None):
        """Creates a lineitem.

        :rtype: :class:`ags.LineItem`
        """
        headers = {
            'Content-Type': 'application/vnd.ims.lis.v2.lineitem+json'
        }

        data = {
            'label': label,
            'scoreMaximum': score_maximum
        }

        if resource_link_id:
            data['resourceLinkId'] = resource_link_id
        if resource_id:
            data['resourceId'] = resource_id
        if tag:
            data['tag'] = tag
        if start_ts:
            data['startDateTime'] = ts2str(start_ts)
        if end_ts:
            data['endDateTime'] = ts2str(end_ts)

        resp = self._client.post(
            self.context._lineitems,
            context=self.context,
            headers=headers,
            json=data
        ).json()

        return LineItem(self, resp, loaded=True)

    def delete(self, lineitem_id):
        """Deletes a lineitem.

        :param lineitem_id: ID (url) of the lineitem
        """
        self._client.delete(
            lineitem_id,
            context=self.context
        )

    def update(self, lineitem_id, data):
        """Updates a lineitem.

        A platform may ignore some changes.

        :param lineitem_id: ID (url) of the lineitem
        :param data: dictionary in 'application/vnd.ims.lis.v2.lineitem+json'
            representation
        :rtype: :class:`ags.LineItem`
        """
        headers = {
            'Content-Type': 'application/vnd.ims.lis.v2.lineitem+json'
        }

        resp = self._client.put(
            lineitem_id,
            context=self.context,
            headers=headers,
            json=data
        ).json()

        return LineItem(self, resp, loaded=True)

    def list(self):
        """Lists lineitems.

        :rtype: list of :class:`ags.LineItem`
        """
        headers = {
            'Accept': 'application/vnd.ims.lis.v2.lineitemcontainer+json'
        }

        resp = self._client.get(
            self.context._lineitems,
            context=self.context,
            headers=headers
        ).json()

        return [LineItem(self, i, loaded=True) for i in resp]

    def get_results(self, lineitem_id):
        """Gets results of a lineitem.

        :param lineitem_id: ID (url) of the lineitem
        :rtype: list of results in
            'application/vnd.ims.lis.v2.resultcontainer+json' representation
        """
        headers = {
            'Accept': 'application/vnd.ims.lis.v2.resultcontainer+json'
        }

        resp = self._client.get(
            self._build_url(lineitem_id, '/results'),
            context=self.context,
            headers=headers
        ).json()

        return resp

    def set_score(self, lineitem_id, score):
        """Sets score of a lineitem.

        :param lineitem_id: ID (url) of the lineitem
        :param score: :class:`ags.Score`
        """
        headers = {
            'Content-Type': 'application/vnd.ims.lis.v1.score+json'
        }

        self._client.post(
            self._build_url(lineitem_id, '/scores'),
            context=self.context,
            headers=headers,
            json=score.to_dict()
        )


class LineItem:
    def __init__(self, manager, data, loaded=False):
        self._manager = manager
        self._loaded = loaded
        self._data = data
        self._add_attrs(data)

    def __setattr__(self, key, value):
        if not key.startswith('_'):
            self._data[key] = value
        super().__setattr__(key, value)

    def _add_attrs(self, data):
        for (key, value) in data.items():
            setattr(self, key, value)

    def load(self):
        """Lazy load this lineitem."""
        self._loaded = True

        lineitem = self._manager.get(self.id)
        if lineitem:
            self._add_attrs(lineitem._data)

    def delete(self):
        """Deletes this lineitem."""
        self._manager.delete(self.id)

    def update(self):
        """Updates this lineitem.

        A platform may ignore some changes.
        """
        lineitem = self._manager.update(self.id, self._data)
        if lineitem:
            self._add_attrs(lineitem._data)

    def get_results(self):
        """Gets results of this lineitem.

        :rtype: list of results in
            'application/vnd.ims.lis.v2.resultcontainer+json' representation
        """
        return self._manager.get_results(self.id)

    def set_score(self, score):
        """Sets score of this lineitem.

        :param score: :class:`ags.Score`
        """
        self._manager.set_score(self.id, score)


class Score:
    def __init__(self, user, score_given=None, score_maximum=100,
                 timestamp=None, activity_progress='Completed',
                 grading_progress='FullyGraded', comment=None):
        self.user = user
        self.score_given = score_given
        self.score_maximum = score_maximum
        self.comment = comment

        if timestamp:
            self.timestamp = ts2str(timestamp)
        else:
            self.timestamp = ts2str(datetime.now())

        valid_activity_progress = [
            'Initialized',
            'Started',
            'InProgress',
            'Submitted',
            'Completed'
        ]

        if activity_progress in valid_activity_progress:
            self.activity_progress = activity_progress
        else:
            raise ValueError(f'Argument activity_progress has to be one of '
                             f'{str(valid_activity_progress)}')

        valid_grading_progress = [
            'NotReady',
            'Failed',
            'PendingManual',
            'Pending',
            'FullyGraded'
        ]

        if grading_progress in valid_grading_progress:
            self.grading_progress = grading_progress
        else:
            raise ValueError(f'Argument grading_progress has to be one of '
                             f'{str(valid_grading_progress)}')

    def to_dict(self):
        score = {
            'userId': self.user.identifier,
            'timestamp': self.timestamp,
            'gradingProgress': self.grading_progress,
            'activityProgress': self.activity_progress
        }

        if self.score_given is not None:
            score['scoreGiven'] = self.score_given
            score['scoreMaximum'] = self.score_maximum

        if self.comment:
            score['comment'] = self.comment

        return score
