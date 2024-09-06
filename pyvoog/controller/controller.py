import re

from stringcase import snakecase

import flask as fl
import marshmallow.exceptions

from sqlalchemy import select, and_, or_

from pyvoog.db import get_session
from pyvoog.exceptions import ValidationError

class Controller:
    DEFAULT_PER_PAGE = 50
    MAX_PER_PAGE = 250

    def permit_attributes(self, schema, payload):

        """ Validate an incoming payload against a Marshmallow schema, return
        the loaded result. Cast validation errors to our ValidationError
        subclass (also thrown on model validation).
        """

        try:
            return schema.load(payload)
        except marshmallow.exceptions.ValidationError as e:
            e.__class__ = ValidationError
            raise

    def paginate(self, query, order_by, descending=False, payload_key=None):

        """ Given an SQLAlchemy statement (`query`) and the name of the column
        determining ordering, paginate output and return a dict. The key of the
        objects array is passed in `payload_key` or deduced automatically from
        the controller name. Pagination metadata is included in `pagination`. If
        `from` is passed in the HTTP query string, this is the ID of the object
        to start output from. The `per_page` parameter controls the maximum
        number of items to output, up to MAX_PER_PAGE. If any further items
        remain after the those output, the ID of the next object is returned in
        the `pagination.next_cursor`. This can be used as the value of `from` to
        the next request.
        """

        model = self.model
        per_page = self._items_per_page
        from_id = fl.request.args.get("from", None)
        ordering_column = getattr(model, order_by)
        empty_result = False
        cursor = None

        query = (
            query
            .order_by(ordering_column.desc() if descending else ordering_column, self.model.id)
            .limit(per_page + 1)
        )

        if from_id:
            query = self._start_pagination_at(query, from_id, ordering_column, descending)

        try:
            *body, _next = get_session().execute(query).scalars()
        except ValueError:
            empty_result = True

        if empty_result:
            payload = []
        elif len(body) < per_page:
            payload = [*body, _next]
        else:
            payload = body
            cursor = _next.id

        if not payload_key:
            payload_key = f'{snakecase(re.sub(r"Controller$", "", self.__class__.__name__))}s'

        return {
            payload_key: payload,
            "pagination": {
                "next_cursor": cursor
            }
        }

    def _start_pagination_at(self, query, from_id, ordering_column, descending):
        model = self.model
        milestone_value = select(ordering_column).where(model.id == from_id).scalar_subquery()
        criterion = ordering_column > milestone_value

        if descending:
            criterion = ordering_column < milestone_value

        return query.where(
            or_(
                criterion,
                and_(ordering_column == milestone_value, model.id >= from_id),
            )
        )

    @property
    def _items_per_page(self):
        try:
            per_page = int(fl.request.args.get("per_page") or self.DEFAULT_PER_PAGE)
        except Exception:
            per_page = self.DEFAULT_PER_PAGE

        return min(max(1, per_page), self.MAX_PER_PAGE)
