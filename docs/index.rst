EasyScrape Documentation
========================

**Web scraping that respects your time.**

EasyScrape is a modern Python library that makes web scraping simple, fast, and reliable.
One line to fetch. One line to extract. Zero boilerplate.

.. code-block:: python

   import easyscrape as es

   result = es.scrape("https://example.com")
   title = result.css("h1")

Quick Links
-----------

* :doc:`quickstart` - Get up and running in 5 minutes
* :doc:`tutorial` - Complete learning guide
* :doc:`api` - Full API reference
* :doc:`cookbook` - Real-world recipes

Installation
------------

.. code-block:: bash

   pip install easyscrape

Requirements: Python 3.10+

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   quickstart
   tutorial

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   configuration
   async
   browser
   cookbook

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
   changelog

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
