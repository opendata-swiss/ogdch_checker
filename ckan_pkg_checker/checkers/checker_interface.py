from abc import ABCMeta, abstractmethod


class CheckerInterface(metaclass=ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'initialize') and
                callable(subclass.initialize) and
                hasattr(subclass, 'check_package') and
                callable(subclass.check_package) and
                hasattr(subclass, 'write_result') and
                callable(subclass.write_result) and
                hasattr(subclass, 'finish') and
                callable(subclass.finish) or
                NotImplemented)

    @abstractmethod
    def initialize(self, *args, **kwargs):
        """Open a file"""
        raise NotImplementedError

    @abstractmethod
    def check_package(self, pkg):
        """Check one data package"""
        raise NotImplementedError

    @abstractmethod
    def write_result(self, *args, **kwargs):
        """Write one result"""
        raise NotImplementedError

    @abstractmethod
    def finish(self):
        """Close the file"""
        raise NotImplementedError
