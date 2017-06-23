Extraction of statistics from the tools-iuc GitHub repository
================

# Usage

## Requirements

- [conda]()
- Create the conda environment:

    ```
    $ conda create -f environment.yml -n tools-iuc-stats
    ```

## Extraction of the GitHub statistics

- Launch the conda environment

    ```
    $ source activate gcc_06_17
    ```

- Generate a Personal access tokens on GitHub (in Setting)
    
- Extract statistics and contributors picture from the GitHub repository

    ```
    $ snakemake --snakefile src/extract_github_info.py
    ```
