"Models and base API"

import operator

from django import VERSION as DJANGO_VERSION
from django.db.models import Q
from django.db import models, transaction
from django.conf import settings

from treebeard.exceptions import InvalidPosition, MissingNodeOrderBy
from polymorphic import PolymorphicModel

#class Node(models.Model):
class Node(PolymorphicModel):
    "Node class"

    def create_node_type(cls, **kwargs):
        if kwargs.has_key('type'):
            klass = kwargs['type']
            assert issubclass(klass, cls.__class__), u'Can only add node descended from %s' % cls.__class__
            kwargs.pop('type')
            newobj = klass(**kwargs)
        else:
            print cls.__class__
            newobj = cls.__class__(**kwargs)

        return newobj

    @classmethod
    def add_root(cls, **kwargs):  # pragma: no cover
        """
        Adds a root node to the tree. The new root node will be the new
        rightmost root node. If you want to insert a root node at a specific
        position, use :meth:`add_sibling` in an already existing root node
        instead.

        :param \*\*kwargs: object creation data that will be passed to the
            inherited Node model

        :returns: the created node object. It will be save()d by this method.
        """
        raise NotImplementedError

    @classmethod
    def load_bulk(cls, bulk_data, parent=None, keep_ids=False):
        """
        Loads a list/dictionary structure to the tree.


        :param bulk_data:

            The data that will be loaded, the structure is a list of
            dictionaries with 2 keys:

            - ``data``: will store arguments that will be passed for object
              creation, and

            - ``children``: a list of dictionaries, each one has it's own
              ``data`` and ``children`` keys (a recursive structure)


        :param parent:

            The node that will receive the structure as children, if not
            specified the first level of the structure will be loaded as root
            nodes


        :param keep_ids:

            If enabled, lads the nodes with the same id that are given in the
            structure. Will error if there are nodes without id info or if the
            ids are already used.


        :returns: A list of the added node ids.
        """

        # tree, iterative preorder
        added = []
        # stack of nodes to analize
        stack = [(parent, node) for node in bulk_data[::-1]]
        while stack:
            parent, node_struct = stack.pop()
            # shallow copy of the data strucure so it doesn't persist...
            node_data = node_struct['data'].copy()
            if keep_ids:
                node_data['id'] = node_struct['id']
            if parent:
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = cls.add_root(**node_data)
            added.append(node_obj.id)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([(node_obj, node) \
                    for node in node_struct['children'][::-1]])
        transaction.commit_unless_managed()
        return added

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):  # pragma: no cover
        """
        Dumps a tree branch to a python data structure.

        :param parent:

            The node whose descendants will be dumped. The node itself will be
            included in the dump. If not given, the entire tree will be dumped.

        :param keep_ids:

            Stores the id value (primary key) of every node. Enabled by
            default.

        :returns: A python data structure, describen with detail in
                  :meth:`load_bulk`
        """
        raise NotImplementedError

    @classmethod
    def get_root_nodes(cls):  # pragma: no cover
        ":returns: A queryset containing the root nodes in the tree."
        raise NotImplementedError

    @classmethod
    def get_first_root_node(cls):
        ":returns: The first root node in the tree or ``None`` if it is empty"
        try:
            return cls.get_root_nodes()[0]
        except IndexError:
            return None

    @classmethod
    def get_last_root_node(cls):
        ":returns: The last root node in the tree or ``None`` if it is empty"
        try:
            return cls.get_root_nodes().reverse()[0]
        except IndexError:
            return None

    @classmethod
    def find_problems(cls):  # pragma: no cover
        "Checks for problems in the tree structure."
        raise NotImplementedError

    @classmethod
    def fix_tree(cls):  # pragma: no cover
        """
        Solves problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.
        """
        raise NotImplementedError

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns: A list of nodes ordered as DFS, including the parent. If
                  no parent is given, the entire tree is returned.
        """
        raise NotImplementedError

    @classmethod
    def get_descendants_group_count(cls, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* (not only children) in every sibling.

        :param parent:

            The parent of the siblings to return. If no parent is given, the
            root nodes will be returned.

        :returns:

            A `list` (**NOT** a Queryset) of node objects with an extra
            attribute: `descendants_count`.
        """

        # this is the slowest possible implementation, subclasses should do
        # better
        if parent is None:
            qset = cls.get_root_nodes()
        else:
            qset = parent.get_children()
        nodes = list(qset)
        for node in nodes:
            node.descendants_count = node.get_descendant_count()
        return nodes

    def get_depth(self):  # pragma: no cover
        ":returns: the depth (level) of the node"
        raise NotImplementedError

    def get_siblings(self):  # pragma: no cover
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        raise NotImplementedError

    def get_children(self):  # pragma: no cover
        ":returns: A queryset of all the node's children"
        raise NotImplementedError

    def get_children_count(self):
        ":returns: The number of the node's children"

        # this is the last resort, subclasses of Node should implement this in
        # a efficient way.
        return self.get_children().count()

    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants, doesn't
            include the node itself (some subclasses may return a list).
        """
        raise NotImplementedError

    def get_descendant_count(self):
        ":returns: the number of descendants of a node."
        return self.get_descendants().count()

    def get_first_child(self):
        ":returns: The leftmost node's child, or None if it has no children."
        try:
            return self.get_children()[0]
        except IndexError:
            return None

    def get_last_child(self):
        ":returns: The rightmost node's child, or None if it has no children."
        try:
            return self.get_children().reverse()[0]
        except IndexError:
            return None

    def get_first_sibling(self):
        """
        :returns: The leftmost node's sibling, can return the node itself if
            it was the leftmost sibling.
        """
        return self.get_siblings()[0]

    def get_last_sibling(self):
        """
        :returns: The rightmost node's sibling, can return the node itself if
            it was the rightmost sibling.
        """
        return self.get_siblings().reverse()[0]

    def get_prev_sibling(self):
        """
        :returns: The previous node's sibling, or None if it was the leftmost
            sibling.
        """

        siblings = self.get_siblings()
        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx > 0:
                return siblings[idx - 1]

    def get_next_sibling(self):
        """
        :returns: The next node's sibling, or None if it was the rightmost
            sibling.
        """
        siblings = self.get_siblings()
        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx < len(siblings) - 1:
                return siblings[idx + 1]

    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node if a sibling of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a sibling
        """
        return len(self.get_siblings().filter(pk__in=[node.pk])) > 0

    def is_child_of(self, node):
        """
        :returns: ``True`` if the node is a child of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a parent
        """
        return len(node.get_children().filter(pk__in=[self.pk])) > 0

    def is_descendant_of(self, node):  # pragma: no cover
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``

        :param node:

            The node that will be checked as an ancestor
        """
        raise NotImplementedError

    def add_child(self, **kwargs):  # pragma: no cover
        """
        Adds a child to the node. The new node will be the new rightmost
        child. If you want to insert a node at a specific position,
        use the :meth:`add_sibling` method of an already existing
        child node instead.

        :param \*\*kwargs:

            Object creation data that will be passed to the inherited Node
            model

        :returns: The created node object. It will be save()d by this method.
        """
        raise NotImplementedError

    def add_sibling(self, pos=None, **kwargs):  # pragma: no cover
        """
        Adds a new node as a sibling to the current node object.


        :param pos:
            The position, relative to the current node object, where the
            new node will be inserted, can be one of:

            - ``first-sibling``: the new node will be the new leftmost sibling
            - ``left``: the new node will take the node's place, which will be
              moved to the right 1 position
            - ``right``: the new node will be inserted at the right of the node
            - ``last-sibling``: the new node will be the new rightmost sibling
            - ``sorted-sibling``: the new node will be at the right position
              according to the value of node_order_by

        :param \*\*kwargs:

            Object creation data that will be passed to the inherited
            Node model

        :returns:

            The created node object. It will be saved by this method.

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling``
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` as ``pos``
           and the :attr:`node_order_by` attribute is missing
        """
        raise NotImplementedError

    def get_root(self):  # pragma: no cover
        ":returns: the root node for the current node object."
        raise NotImplementedError

    def is_root(self):
        ":returns: True if the node is a root node (else, returns False)"
        return self.get_root() == self

    def is_leaf(self):
        ":returns: True if the node is a leaf node (else, returns False)"
        return self.get_children_count() == 0

    def get_ancestors(self):  # pragma: no cover
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
            (some subclasses may return a list)
        """
        raise NotImplementedError

    def get_parent(self, update=False):  # pragma: no cover
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.

        :param update: Updates de cached value.
        """
        raise NotImplementedError

    def move(self, target, pos=None):  # pragma: no cover
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        :param target:

            The node that will be used as a relative child/sibling when moving

        :param pos:

            The position, relative to the target node, where the
            current node object will be moved to, can be one of:

            - ``first-child``: the node will be the new leftmost child of the
              ``target`` node
            - ``last-child``: the node will be the new rightmost child of the
              ``target`` node
            - ``sorted-child``: the new node will be moved as a child of the
              ``target`` node according to the value of :attr:`node_order_by`
            - ``first-sibling``: the node will be the new leftmost sibling of
              the ``target`` node
            - ``left``: the node will take the ``target`` node's place, which
              will be moved to the right 1 position
            - ``right``: the node will be moved to the right of the ``target``
              node
            - ``last-sibling``: the node will be the new rightmost sibling of
              the ``target`` node
            - ``sorted-sibling``: the new node will be moved as a sibling of
              the ``target`` node according to the value of
              :attr:`node_order_by`

            .. note:: If no ``pos`` is given the library will use
                     ``last-sibling``, or ``sorted-sibling`` if
                     :attr:`node_order_by` is enabled.

        :returns: None

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling`` or ``sorted-child``
        :raise InvalidMoveToDescendant: when trying to move a node to one of
           it's own descendants
        :raise PathOverflow: when the library can't make room for the
           node's new position
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` or
           ``sorted-child`` as ``pos`` and the :attr:`node_order_by`
           attribute is missing
        """
        raise NotImplementedError

    def delete(self):
        "Removes a node and all it's descendants."
        self.__class__.objects.filter(id=self.id).delete()

    def _fix_add_sibling_opts(self, pos):
        "prepare the pos variable for the add_sibling method"
        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in ('first-sibling', 'left', 'right', 'last-sibling',
                       'sorted-sibling'):
            raise InvalidPosition('Invalid relative position: %s' % (pos, ))
        if self.node_order_by and pos != 'sorted-sibling':
            raise InvalidPosition('Must use %s in add_sibling when'
                                  ' node_order_by is enabled' % (
                                  'sorted-sibling', ))
        if pos == 'sorted-sibling' and not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')
        return pos

    def _fix_move_opts(self, pos):
        "prepare the pos var for the move method"
        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in ('first-sibling', 'left', 'right', 'last-sibling',
                       'sorted-sibling', 'first-child', 'last-child',
                       'sorted-child'):
            raise InvalidPosition('Invalid relative position: %s' % (pos, ))
        if self.node_order_by and pos not in ('sorted-child',
                                              'sorted-sibling'):
            raise InvalidPosition('Must use %s or %s in add_sibling when'
                                  ' node_order_by is enabled' % (
                                  'sorted-sibling', 'sorted-child'))
        if pos in ('sorted-child', 'sorted-sibling') and \
                not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')
        return pos

    def get_sorted_pos_queryset(self, siblings, newobj):
        """
        :returns: A queryset of the nodes that must be moved
        to the right. Called only for Node models with :attr:`node_order_by`

        This function was taken from django-mptt (BSD licensed) by Jonathan
        Buchanan:
        http://code.google.com/p/django-mptt/source/browse/trunk/mptt/signals.py?spec=svn100&r=100#12
        """

        fields, filters = [], []
        for field in self.node_order_by:
            value = getattr(newobj, field)
            filters.append(Q(*
                [Q(**{f: v}) for f, v in fields] +
                [Q(**{'%s__gt' % field: value})]))
            fields.append((field, value))
        return siblings.filter(reduce(operator.or_, filters))

    @classmethod
    def get_annotated_list(cls, parent=None):
        """
        Gets an annotated list from a tree branch.

        :param parent:

            The node whose descendants will be annotated. The node itself
            will be included in the list. If not given, the entire tree
            will be annotated.
        """

        result, info = [], {}
        start_depth, prev_depth = (None, None)

        for node in cls.get_tree(parent):

            depth = node.get_depth()

            if start_depth is None:
                start_depth = depth

            open = (depth > prev_depth)

            if depth < prev_depth:
                info['close'] = range(0, prev_depth - depth)

            info = {'open': open, 'close': [], 'level': depth - start_depth}

            result.append((node, info,))

            prev_depth = depth

        if start_depth > 0:
            info['close'] = range(0, prev_depth - start_depth + 1)

        return result

    @classmethod
    def _get_serializable_model(cls):
        """
        Returns a model with a valid _meta.local_fields (serializable).

        Basically, this means the original model, not a proxied model.

        (this is a workaround for a bug in django)
        """
        if DJANGO_VERSION >= (1, 1):
            while cls._meta.proxy:
                cls = cls._meta.proxy_for_model
        return cls

    @classmethod
    def get_database_engine(cls):
        """
        Returns the supported database engine used by a treebeard model.

        This will return the default database engine depending on the version
        of Django. If you use something different, like a non-default database
        in Django 1.2+, you need to override this method and return the correct
        engine.

        :returns: postgresql, postgresql_psycopg2, mysql or sqlite3
        """
        engine = None
        if DJANGO_VERSION >= (1, 2):
            try:
                engine = settings.DATABASES['default']['ENGINE']
            except AttributeError, KeyError:
                engine = None
            # the old style settings still work in Django 1.2+ if there is no
            # DATABASES setting
        if engine is None:
            engine = settings.DATABASE_ENGINE
        return engine.split('.')[-1]


    class Meta:
        "Abstract model."
        abstract = True
