#!/usr/bin/env python
##############################################################################
#
# diffpy.pdfmorph   by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2010 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Chris Farrow
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
##############################################################################

from __future__ import print_function

import sys
from pathlib import Path

import numpy
from diffpy.pdfmorph.version import __version__
import diffpy.pdfmorph.tools as tools
import diffpy.pdfmorph.pdfplot as pdfplot
import diffpy.pdfmorph.morphs as morphs
import diffpy.pdfmorph.morph_helpers as helpers
import diffpy.pdfmorph.refine as refine


def create_option_parser():
    import optparse
    prog_short = Path(sys.argv[0]).name  # Program name, compatible w/ all OS paths

    class CustomParser(optparse.OptionParser):
        def __init__(self, *args, **kwargs):
            super(CustomParser, self).__init__(*args, **kwargs)

        def custom_error(self, msg):
            """custom_error(msg : string)

            Print a message incorporating 'msg' to stderr and exit.
            Does not print usage.
            """
            self.exit(2, "%s: error: %s\n" % (self.get_prog_name(), msg))

    parser = CustomParser(
        usage='\n'.join(
            [
                "%prog [options] FILE1 FILE2",
                "Manipulate and compare PDFs.",
                "Use --help for help.",
            ]
        ),
        epilog="Please report bugs to diffpy-dev@googlegroups.com.",
    )

    parser.add_option(
        '-V', '--version', action="version", help="Show program version and exit."
    )
    parser.version = __version__
    parser.add_option(
        '-s',
        '--save',
        metavar="NAME",
        dest="saveloc",
        help="""Save the manipulated PDF to a file named NAME. Use \'-\' for stdout.
When --multiple is enabled, save each manipulated PDF as a file in a directory named NAME;
you can specify names for each saved PDF file using --save-names-file.""",
    )
    parser.add_option(
        '--snf',
        '--save-names-file',
        metavar="NAMESFILE",
        dest="snfile",
        help="""Used only when both -s and --multiple are enabled.
Specify names for each manipulated PDF when saving (see -s) using a serial file
NAMESFILE. The format of NAMESFILE should be as follows: each target PDF
is an entry in NAMESFILE. For each entry, there should be a key 'save_morph_as'
whose value specifies the name to save the manipulated PDF as.
(See sample names files in the pdfmorph tutorial).""",
    )
    parser.add_option(
        '-v',
        '--verbose',
        dest="verbose",
        action="store_true",
        help="Print additional header details to saved files.",
    )
    parser.add_option(
        '--multiple',
        dest="multiple",
        action="store_true",
        help=f"""Changes usage to \'{prog_short} [options] FILE DIRECTORY\'. FILE
will be morphed with each file in DIRECTORY as target.
Files in DIRECTORY are sorted by alphabetical order unless a field is
specified by --sort-by. See -s and Plot Options for how saving and
plotting change when this option is enabled.""",
    )
    parser.add_option(
        '--sort-by',
        metavar="FIELD",
        dest="field",
        help="""Used with --multiple to sort files in DIRECTORY by FIELD from lowest to highest.
FIELD must be included in the header of all the PDF files.""",
    )
    parser.add_option(
        '--reverse',
        dest="reverse",
        action="store_true",
        help="""Sort from highest to lowest instead.""",
    )
    parser.add_option(
        '--serial-file',
        metavar="SERIAL",
        dest="serfile",
        help="""Look for FIELD in a serial file instead.
Must specify name of serial file SERIAL.""",
    )
    parser.add_option(
        '--rmin', type="float", help="Minimum r-value to use for PDF comparisons."
    )
    parser.add_option(
        '--rmax', type="float", help="Maximum r-value to use for PDF comparisons."
    )
    parser.add_option(
        '--pearson',
        action="store_true",
        dest="pearson",
        help="Maximize agreement in the Pearson function. Note that this is insensitive to scale.",
    )
    parser.add_option(
        '--addpearson',
        action="store_true",
        dest="addpearson",
        help="""Maximize agreement in the Pearson function as well as
minimizing the residual.""",
    )

    # Manipulations
    group = optparse.OptionGroup(
        parser,
        "Manipulations",
        """These options select the manipulations that are to be applied to
the PDF from FILE1. The passed values will be refined unless specifically
excluded with the -a or -x options. If no option is specified, the PDFs from FILE1 and FILE2 will
be plotted without any manipulations.""",
    )
    parser.add_option_group(group)
    group.add_option(
        '-a',
        '--apply',
        action="store_false",
        dest="refine",
        help="Apply manipulations but do not refine.",
    )
    group.add_option(
        '-x',
        '--exclude',
        action="append",
        dest="exclude",
        metavar="MANIP",
        help="""Exclude a manipulation from refinement by name. This can
appear multiple times.""",
    )
    group.add_option(
        '--scale', type="float", metavar="SCALE", help="Apply scale factor SCALE."
    )
    group.add_option(
        '--smear',
        type="float",
        metavar="SMEAR",
        help="Smear peaks with a Gaussian of width SMEAR.",
    )
    group.add_option(
        '--stretch',
        type="float",
        metavar="STRETCH",
        help="Stretch PDF by a fraction STRETCH.",
    )
    group.add_option(
        '--slope',
        type="float",
        dest="baselineslope",
        help="""Slope of the baseline. This is used when applying the smear
factor. It will be estimated if not provided.""",
    )
    group.add_option(
        '--qdamp',
        type="float",
        metavar="QDAMP",
        help="Dampen PDF by a factor QDAMP. (See PDFGui manual.)",
    )
    group.add_option(
        '--radius',
        type="float",
        metavar="RADIUS",
        help="""Apply characteristic function of sphere with radius RADIUS.
If PRADIUS is also specified, instead apply characteristic function of spheroid with equatorial radius RADIUS and polar radius PRADIUS.""",
    )
    group.add_option(
        '--pradius',
        type="float",
        metavar="PRADIUS",
        help="""Apply characteristic function of spheroid with equatorial
radius RADIUS and polar radius PRADIUS. If only PRADIUS is specified, instead apply characteristic function of sphere with radius PRADIUS.""",
    )
    group.add_option(
        '--iradius',
        type="float",
        metavar="IRADIUS",
        help="""Apply inverse characteristic function of sphere with radius IRADIUS.  If IPRADIUS is also specified, instead apply inverse characteristic function of spheroid with equatorial radius IRADIUS and polar radius IPRADIUS.""",
    )
    group.add_option(
        '--ipradius',
        type="float",
        metavar="IPRADIUS",
        help="""Apply inverse characteristic function of spheroid with equatorial radius IRADIUS and polar radius IPRADIUS. If only IPRADIUS is specified, instead apply inverse characteristic function of sphere with radius IPRADIUS.""",
    )

    # Plot Options
    group = optparse.OptionGroup(
        parser, "Plot Options", """These options control plotting.
The manipulated and target PDFs will be plotted against each other with a
difference curve below. When --multiple is enabled, a plot of Rw values for
each file will be shown instead."""
    )
    parser.add_option_group(group)
    group.add_option(
        '-n',
        '--noplot',
        action="store_false",
        dest="plot",
        help="""Do not show a plot.""",
    )
    group.add_option(
        '--mlabel',
        metavar="MLABEL",
        dest="mlabel",
        help="Set label for morphed data to MLABEL on plot. Ignored if using file names as labels.",
    )
    group.add_option(
        '--tlabel',
        metavar="TLABEL",
        dest="tlabel",
        help="Set label for target data to TLABEL on plot. Ignored if using file names as labels.",
    )
    group.add_option(
        '--pmin', type="float", help="Minimum r-value to plot. Defaults to RMIN."
    )
    group.add_option(
        '--pmax', type="float", help="Maximum r-value to plot. Defaults to RMAX."
    )
    group.add_option(
        '--maglim', type="float", help="Magnify plot curves beyond MAGLIM by MAG."
    )
    group.add_option(
        '--mag', type="float", help="Magnify plot curves beyond MAGLIM by MAG."
    )
    group.add_option(
        '--lwidth', type="float", help="Line thickness of plotted curves."
    )

    # Defaults
    parser.set_defaults(multiple=False)
    parser.set_defaults(reverse=False)
    parser.set_defaults(plot=True)
    parser.set_defaults(refine=True)
    parser.set_defaults(pearson=False)
    parser.set_defaults(addpearson=False)
    parser.set_defaults(mag=5)
    parser.set_defaults(lwidth=1.5)

    return parser


def single_morph(parser, opts, pargs, stdout_flag=True):
    if len(pargs) < 2:
        parser.error("You must supply FILE1 and FILE2.")
    elif len(pargs) > 2:
        parser.error("Too many arguments. Make sure you only supply FILE1 and FILE2.")

    # Get the PDFs
    x_morph, y_morph = getPDFFromFile(pargs[0])
    x_target, y_target = getPDFFromFile(pargs[1])

    # Get configuration values
    scale_in = 'None'
    stretch_in = 'None'
    smear_in = 'None'
    config = {}
    config["rmin"] = opts.rmin
    config["rmax"] = opts.rmax
    config["rstep"] = None
    if opts.rmin is not None and opts.rmax is not None and opts.rmax <= opts.rmin:
        e = "rmin must be less than rmax"
        parser.custom_error(e)

    # Set up the morphs
    chain = morphs.MorphChain(config)
    # Add the r-range morph, we will remove it when saving and plotting
    chain.append(morphs.MorphRGrid())
    refpars = []

    ## Scale
    if opts.scale is not None:
        scale_in = opts.scale
        chain.append(morphs.MorphScale())
        config["scale"] = opts.scale
        refpars.append("scale")
    ## Stretch
    if opts.stretch is not None:
        stretch_in = opts.stretch
        chain.append(morphs.MorphStretch())
        config["stretch"] = opts.stretch
        refpars.append("stretch")
    ## Smear
    if opts.smear is not None:
        smear_in = opts.smear
        chain.append(helpers.TransformXtalPDFtoRDF())
        chain.append(morphs.MorphSmear())
        chain.append(helpers.TransformXtalRDFtoPDF())
        refpars.append("smear")
        config["smear"] = opts.smear
        config["baselineslope"] = opts.baselineslope
        if opts.baselineslope is None:
            refpars.append("baselineslope")
            config["baselineslope"] = -0.5
    ## Size
    radii = [opts.radius, opts.pradius]
    nrad = 2 - radii.count(None)
    if nrad == 1:
        radii.remove(None)
        config["radius"] = tools.nn_value(radii[0], "radius or pradius")
        chain.append(morphs.MorphSphere())
        refpars.append("radius")
    elif nrad == 2:
        config["radius"] = tools.nn_value(radii[0], "radius")
        refpars.append("radius")
        config["pradius"] = tools.nn_value(radii[1], "pradius")
        refpars.append("pradius")
        chain.append(morphs.MorphSpheroid())
    iradii = [opts.iradius, opts.ipradius]
    inrad = 2 - iradii.count(None)
    if inrad == 1:
        iradii.remove(None)
        config["iradius"] = tools.nn_value(iradii[0], "iradius or ipradius")
        chain.append(morphs.MorphISphere())
        refpars.append("iradius")
    elif inrad == 2:
        config["iradius"] = tools.nn_value(iradii[0], "iradius")
        refpars.append("iradius")
        config["ipradius"] = tools.nn_value(iradii[1], "ipradius")
        refpars.append("ipradius")
        chain.append(morphs.MorphISpheroid())

    ## Resolution
    if opts.qdamp is not None:
        chain.append(morphs.MorphResolutionDamping())
        refpars.append("qdamp")
        config["qdamp"] = opts.qdamp

    # Now remove non-refinable parameters
    if opts.exclude is not None:
        refpars = set(refpars) - set(opts.exclude)
        refpars = list(refpars)

    # Refine or execute the morph
    refiner = refine.Refiner(chain, x_morph, y_morph, x_target, y_target)
    if opts.pearson:
        refiner.residual = refiner._pearson
    if opts.addpearson:
        refiner.residual = refiner._add_pearson
    if opts.refine and refpars:
        try:
            # This works better when we adjust scale and smear first.
            if "smear" in refpars:
                rptemp = ["smear"]
                if "scale" in refpars:
                    rptemp.append("scale")
                refiner.refine(*rptemp)
            refiner.refine(*refpars)
        except ValueError as e:
            parser.custom_error(str(e))
    elif "smear" in refpars and opts.baselineslope is None:
        try:
            refiner.refine("baselineslope", baselineslope=-0.5)
        except ValueError as e:
            parser.custom_error(str(e))
    else:
        chain(x_morph, y_morph, x_target, y_target)

    # Get Rw for the morph range
    rw = tools.getRw(chain)
    pcc = tools.get_pearson(chain)
    # Replace the MorphRGrid with Morph identity
    chain[0] = morphs.Morph()
    chain(x_morph, y_morph, x_target, y_target)

    morphs_in = "\n# Input morphing parameters:"
    morphs_in += f"\n# scale = {scale_in}"
    morphs_in += f"\n# stretch = {stretch_in}"
    morphs_in += f"\n# smear = {smear_in}\n"

    # Output morph parameters
    morph_results = dict(config.items())

    # Ensure Rw, Pearson last two outputs
    morph_results.update({"Rw": rw})
    morph_results.update({"Pearson": pcc})

    morphs_out = "# Optimized morphing parameters:\n"
    morphs_out += "\n".join(f"# {key} = {morph_results[key]:.6f}" for key in morph_results.keys())

    # No stdout output when running morph multiple
    if stdout_flag:
        print(f"{morphs_in}\n{morphs_out}\n")

    if opts.saveloc is not None:
        path_name = Path(pargs[0]).resolve().as_posix()
        header = "# PDF created by pdfmorph\n"
        header += f"# from {path_name}"

        header_verbose = f"{morphs_in}\n{morphs_out}"

        # Save to file
        try:
            if opts.saveloc != "-":
                save_file_name = Path(opts.saveloc).resolve().as_posix()
                with open(opts.saveloc, 'w') as outfile:
                    # Print out a header (more if verbose)
                    print(header, file=outfile)
                    if opts.verbose:
                        print(header_verbose, file=outfile)

                    # Print table with label
                    print("\n# Labels: [r] [gr]", file=outfile)
                    numpy.savetxt(outfile, numpy.transpose([chain.x_morph_out, chain.y_morph_out]))

                    if stdout_flag:
                        # Indicate successful save to terminal
                        save_message = f"# Morph saved to {save_file_name}\n"
                        print(save_message)

            else:
                # Just print table with label if save is to stdout
                print("# Labels: [r] [gr]")
                numpy.savetxt(sys.stdout, numpy.transpose([chain.x_morph_out, chain.y_morph_out]))
        except FileNotFoundError as e:
            save_fail_message = "Unable to save to designated location."
            print(save_fail_message)
            parser.custom_error(str(e))

    if opts.plot:
        pairlist = [chain.xy_morph_out, chain.xy_target_out]
        labels = [pargs[0], pargs[1]]  # Default is to use file names

        # If user chooses labels
        if opts.mlabel is not None:
            labels[0] = opts.mlabel
        if opts.tlabel is not None:
            labels[1] = opts.tlabel

        # Plot extent defaults to calculation extent
        pmin = opts.pmin if opts.pmin is not None else opts.rmin
        pmax = opts.pmax if opts.pmax is not None else opts.rmax
        maglim = opts.maglim
        mag = opts.mag
        l_width = opts.lwidth
        pdfplot.comparePDFs(
            pairlist, labels, rmin=pmin, rmax=pmax, maglim=maglim, mag=mag, rw=rw, l_width=l_width
        )

    return morph_results


def multiple_morphs(parser, opts, pargs, stdout_flag=True):
    # Custom error messages since usage is distinct when --multiple tag is applied
    if len(pargs) < 2:
        parser.custom_error("You must supply FILE and DIRECTORY. See --multiple under --help for usage.")
    elif len(pargs) > 2:
        parser.custom_error("Too many arguments. You must only supply a FILE and a DIRECTORY.")

    # Parse paths
    morph_file = Path(pargs[0])
    if not morph_file.is_file():
        parser.custom_error(f"{morph_file} is not a file. Go to --help for usage.")
    target_directory = Path(pargs[1])
    if not target_directory.is_dir():
        parser.custom_error(f"{target_directory} is not a directory. Go to --help for usage.")

    # Do not morph morph_file against itself if it is in the same directory
    target_list = list(target_directory.iterdir())
    if morph_file in target_list:
        target_list.remove(morph_file)

    # Format field name for printing and plotting
    field = None
    if opts.field is not None:
        field_words = opts.field.split()
        field = ""
        for word in field_words:
            field += f"{word[0].upper()}{word[1:].lower()}"
    field_list = None

    # Sort files in directory by some field
    if field is not None:
        try:
            target_list, field_list = tools.field_sort(target_list, field, opts.reverse, opts.serfile,
                                                       get_field_values=True)
        except KeyError:
            if opts.serfile is not None:
                parser.custom_error("The requested field was not found in the metadata file.")
            else:
                parser.custom_error("The requested field is missing from a PDF file header.")
    else:
        # Default is alphabetical sort
        target_list.sort(reverse=opts.reverse)

    # Disable single morph plotting
    plot_opt = opts.plot
    opts.plot = False

    # Manage saving
    save_opt = opts.saveloc
    save_names = {}
    save_morphs_here = ""
    if save_opt is not None:
        try:
            # Make directory to save files in if it does not already exist
            Path(save_opt).mkdir(parents=True, exist_ok=True)

            # Morphs will be saved in the subdirectory "Morphs"
            save_morphs_here = Path(save_opt).joinpath("Morphs")
            save_morphs_here.mkdir(exist_ok=True)

            # Get names for the saved morphs
            if opts.snfile is not None:
                # Names should be stored properly in opts.snfile
                save_names = tools.deserialize(opts.snfile)
            # Default naming scheme
            else:
                for target_file in target_list:
                    save_names.update({target_file.name: {"save_morph_as":
                                                          f"Morph_with_Target_{target_file.stem}.cgr"}})

        # Save failed
        except FileNotFoundError as e:
            save_fail_message = "\nUnable to create directory"
            print(save_fail_message)
            parser.custom_error(str(e))

    # Morph morph_file against all other files in target_directory
    results = {}
    for target_file in target_list:
        if target_file.is_file:
            # Set the save file destination to be a file within the SLOC directory
            if save_opt is not None:
                opts.saveloc = Path(save_morphs_here).joinpath(save_names.get(target_file.name).get("save_morph_as"))
            # Perform a morph of morph_file against target_file
            pargs = [morph_file, target_file]
            results.update({
                target_file.name:
                    single_morph(parser, opts, pargs, stdout_flag=False),
            })

    # Parse all parameters from results
    file_names = []
    results_length = len(results.keys())
    for key in results.keys():
        file_names.append(key)
    scales = tools.get_values_from_dictionary_collection(results, "scale")
    smears = tools.get_values_from_dictionary_collection(results, "smear")
    stretches = tools.get_values_from_dictionary_collection(results, "stretch")
    pearsons = tools.get_values_from_dictionary_collection(results, "pearson")
    rws = tools.get_values_from_dictionary_collection(results, "rw")

    # Input parameters used for every morph
    inputs = [None, None]
    inputs[0] = f"# Morphed file: {morph_file.name}"
    inputs[1] = "\n# Input morphing parameters:"
    inputs[1] += f"\n# scale = {opts.scale}"
    inputs[1] += f"\n# stretch = {opts.stretch}"
    inputs[1] += f"\n# smear = {opts.smear}"
    input_header = f"{inputs[0]}{inputs[1]}\n"

    # Verbose to get output for every morph
    verbose_header = ""
    if opts.verbose:
        # Output for every morph (information repeated in a succint table below)
        for key in results.keys():
            outputs = f"\n# Target: {key}\n"
            outputs += "# Optimized morphing parameters:\n"
            outputs += "\n".join(f"# {param} = {results[key][param]:.6f}" for param in results[key].keys())
            verbose_header += f"{outputs}\n"

    # Table labels
    labels = "\n# Labels: [Target]"
    if field is not None:
        labels += f" [{field}]"
    for param in [["Scale", scales], ["Stretch", stretches], ["Smear", smears]]:
        if len(param[1]) > 0:
            labels += f" [{param[0]}]"
    labels += " [Pearson] [Rw]\n"

    # Corresponding table
    table = ""
    for idx in range(results_length):
        row = f"{file_names[idx]}"
        if field is not None:
            row += f" {field_list[idx]}"
        for param in [scales, stretches, smears]:
            if len(param) > idx:
                row += f" {param[idx]:0.6f}"
        row += f" {pearsons[idx]:0.6f} {rws[idx]:0.6f}"
        table += f"{row}\n"

    # Print only if print requested
    if stdout_flag:
        print(f"\n{input_header}{verbose_header}{labels}{table}")

    # Also save the table as a csv in the SLOC directory if -s enabled
    if save_opt:
        reference_table = Path(save_opt).joinpath("Morph_Reference_Table.csv")
        with open(reference_table, 'w') as reference:
            print(f"{input_header}{verbose_header}{labels}{table}", file=reference)
            save_message = f"# Morphs saved to the directory {save_morphs_here.resolve().as_posix()}\n"
            print(save_message)

    # Plot the rw table if requested
    if plot_opt:
        if field_list is not None:
            pdfplot.plot_rws(field_list, rws, field)
        else:
            pdfplot.plot_rws(file_names, rws)

    return results


def getPDFFromFile(fn):
    from diffpy.pdfmorph.tools import readPDF

    try:
        r, gr = readPDF(fn)
    except IOError as errmsg:
        print("%s: %s" % (fn, errmsg), file=sys.stderr)
        sys.exit(1)
    except ValueError:
        print("Cannot read %s" % fn, file=sys.stderr)
        sys.exit(1)

    return r, gr


def main():
    parser = create_option_parser()
    (opts, pargs) = parser.parse_args()
    if opts.multiple:
        multiple_morphs(parser, opts, pargs, stdout_flag=True)
    else:
        single_morph(parser, opts, pargs, stdout_flag=True)


if __name__ == "__main__":
    main()
