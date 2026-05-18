#!/usr/bin/env python3
import sys

if len(sys.argv) > 1:
    from tally_xml_client.cli import main
    main()
else:
    from tally_xml_client.gui import launch
    launch()
