.. _naming-conventions:

############################
 Dataset naming conventions
############################

.. note::

   This is a draft proposal for naming conventions for datasets in the
   Anemoi registry. It will need to be updated and adapted as more
   datasets are added. The part <purpose> is especially difficult to
   define for some dataset and may be revisited.

A dataset name is built as follow:
<purpose>-<content>-<source>-<resolution>-<start_year>-<end-year>-<frequency>-v<version>[-<optional-string>].zarr
The <content> is built from several parts, separated with '-'. All lower
case. Uses "-", letters and numbers. No underscores "_", no dots "."

Example: aifs-od-an-oper-0001-mars-o96-1979-2022-1h-v5 <purpose> = aifs
because the data is used to train the AIFS model. <content> The content
of the dataset CAN have four parts, such as:
<class>-<type>-<stream><expver> <class>= od Operational archive ("class"
is a MARS keyword) <type> = an Analysis ("type" is a MARS keyword)
<stream> = oper Atmospheric model ("stream" is a MARS keyword) <expver>
= 0001 (operational model) <source> = mars (data is from MARS), could be
"opendap" or other. <resolution> = o96 (other : n320, 0p2 for 0.2
degree) <start_year>-<end-year> = 1979-2022 (or 2020-2020 for if all the
data is included in the year 2020) <frequency> = 1h (other : 6h)
<version> = This version of the content of the dataset, e.g. which
variables, levels, etc, this is not the version of the format.
<optional-string> = Experimental datasets can have additional text in
the name.
