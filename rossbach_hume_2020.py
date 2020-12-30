#!/usr/bin/env python3
from skbio.stats.ordination import pcoa
import matplotlib as mpl
mpl.use('TKAgg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import itertools
import seaborn as sb

DEGREE_SIGN = u'\N{DEGREE SIGN}'

class Susann:
    def __init__(self):

        fig, ax = plt.subplots(1,3, figsize=(16,5))
        path_to_dist = '2020-06-09_11-59-06.357078_braycurtis_sample_distances_A_sqrt.dist'
        path_to_meta = '109_20200609_2020-06-09_11-59-06.357078.seqs.absolute.meta_only.txt'
        path_to_profile = '109_20200609_2020-06-09_11-59-06.357078.profiles.absolute.abund_and_meta.txt'
        profile_df = pd.read_table(path_to_profile, skiprows=6, index_col=1)
        profile_df = profile_df.iloc[:-2].astype(float).astype(int)
        a1_samples = list(profile_df[profile_df['A1'] != 0].index)

        with open(path_to_dist, 'r') as f:
            d = [_.rstrip().split('\t') for _ in f]
        samples = [_[0] for _ in d]
        ids = [_[1] for _ in d]
        data = [_[2:] for _ in d]
        dist_df = pd.DataFrame(data, index=samples, columns=samples).astype(float)
        to_drop = ['S1_H2O', 'S3_H2O', 'extraction_neg', 'milliq_neg']
        dist_df = dist_df.drop(columns=to_drop, index=to_drop)
        
        meta_df = pd.read_csv(path_to_meta, sep='\t')
        meta_df = meta_df.iloc[:-3,]
        meta_df.set_index('sample_name', drop=True, inplace=True)
        meta_df = meta_df.drop(index=to_drop)
        meta_df = meta_df.loc[:,['collection_latitude', 'collection_longitude']]
        meta_df['loc'] = [f'{latitude},{longitude}' for longitude, latitude in zip(meta_df['collection_longitude'], meta_df['collection_latitude'])]
        meta_df.sort_values(by='collection_latitude', inplace=True, ascending=False)
        unique_loc = meta_df['loc'].unique()
        site_names = [f'29{DEGREE_SIGN} Gulf of Aqaba', f'27{DEGREE_SIGN} Duba', 'Thuwal', 'Al Lith', 'Farasan Banks']
        loc_to_site_dict = {loc: site_name for loc, site_name in zip(unique_loc, site_names)}

        # now run the pcoa
        pcoa_df_raw = pcoa(dist_df)
        pcoa_df = pcoa_df_raw.samples
        pcoa_df.index = dist_df.index
        colours = []
        # We want to differentiate between the sites with symbols as well as colours
        # for colourblind.
        shape_dict = {loc: symbol for loc, symbol in zip(unique_loc, reversed(["o", "s", "+", "^", "1"]),)}
        cols = reversed([d['color'] for d in list(mpl.rcParams["axes.prop_cycle"][:len(site_names)])])
        col_dict = {loc: col for loc, col in zip(unique_loc, cols)}
        for loc in unique_loc:
            samples = meta_df[meta_df['loc'] == loc].index
            scat = ax[0].plot(pcoa_df.loc[samples, 'PC1'], pcoa_df.loc[samples, 'PC2'], linestyle='none',
                                 label=loc, marker=shape_dict[loc], fillstyle='none', c=col_dict[loc])
            colours.append(scat[0].get_color())
        ax[0].set_xlabel(f'PC1 {pcoa_df_raw.proportion_explained[0]:.2f}')
        ax[0].set_ylabel(f'PC2 {pcoa_df_raw.proportion_explained[1]:.2f}')

        # Plot an arrow next to the A1 samples
        a1_samples_pcoa_one = [_ for _ in pcoa_df.index if _ in a1_samples]
        scat = ax[0].plot(pcoa_df.loc[a1_samples_pcoa_one, 'PC1'] + 0.04, pcoa_df.loc[a1_samples_pcoa_one, 'PC2'],
                          linestyle='none', marker='<', c='black')

        for loc, c in zip(unique_loc, colours):
            samples = meta_df[meta_df['loc'] == loc].index
            ax[1].plot(pcoa_df.loc[samples, 'PC1'], pcoa_df.loc[samples, 'PC3'], c=c, label=loc_to_site_dict[loc],
                       linestyle='none', marker=shape_dict[loc], fillstyle='none')
        ax[1].set_xlabel(f'PC1 {pcoa_df_raw.proportion_explained[0]:.2f}')
        ax[1].set_ylabel(f'PC3 {pcoa_df_raw.proportion_explained[2]:.2f}')
        
        ax[1].legend(loc='upper right', fontsize='x-small')

        # Plot an arrow next to the A1 samples
        scat = ax[1].plot(pcoa_df.loc[a1_samples_pcoa_one, 'PC1'] + 0.04, pcoa_df.loc[a1_samples_pcoa_one, 'PC3'],
                          linestyle='none', marker='<', c='black')

        self._set_lims(ax=ax[0])
        self._set_lims(ax=ax[1])
        ax[0].set_aspect('equal', 'box')
        ax[1].set_aspect('equal', 'box')
        # I want to add an additional figure here which will be better for quantifying
        # the distances between and within the sites. For each site I want to have
        # one bar that is coloured the same colour of the site, one bar for each of the other
        # sites, and then finally a grey bar.
        # The bar that is the colour as the site in question will show the average within site
        # distance. For each of the other sites, it will give the average between sites
        # Finally it will give the average betweeen all other sites as a grey bar.

        # we can put the results into a df where each row is a site and the columns
        # are the sites plus one extra for the overall average distance
        cols = list(unique_loc)
        cols.append('between_all')
        result_df = pd.DataFrame(index=unique_loc, columns=cols)
        stdev_df = pd.DataFrame(index=unique_loc, columns=cols)
        for site_self in result_df.index:
            for site_compare in list(result_df):
                # Here we do the computations
                if site_self == site_compare:
                    # Then we want to be doing the within site average distance
                    # Get a list of the sites
                    samples = meta_df[meta_df['loc']==site_self].index
                    tot_dist = [dist_df.at[site_1, site_2] for (site_1, site_2) in itertools.combinations(samples, 2)]
                    result_df.at[site_self, site_compare] = sum(tot_dist)/len(tot_dist)
                    stdev_df.at[site_self, site_compare] = np.std(tot_dist)
                elif site_compare == 'between_all':
                    # then we want to be doing the overall distance to other sites
                    samples = meta_df[meta_df['loc']==site_self].index
                    other_samples = meta_df[meta_df['loc']!=site_self].index
                    tot_dist = []
                    for s in samples:
                        for o_s in other_samples:
                            tot_dist.append(dist_df.at[s, o_s])
                    result_df.at[site_self, site_compare] = sum(tot_dist)/len(tot_dist)
                    stdev_df.at[site_self, site_compare] = np.std(tot_dist)
                else:
                    # Then we want to be doing the specific between site average distance
                    samples_in = meta_df[meta_df['loc'] == site_self].index
                    samples_out = meta_df[meta_df['loc'] == site_compare].index
                    tot_dist = []
                    for s_in in samples_in:
                        for s_out in samples_out:
                            tot_dist.append(dist_df.at[s_in, s_out])
                    result_df.at[site_self, site_compare] = sum(tot_dist)/len(tot_dist)
                    stdev_df.at[site_self, site_compare] = np.std(tot_dist)
        # for mat df
        result_df = result_df.astype(float)
        result_df.columns = [loc_to_site_dict[_] if _ in loc_to_site_dict else 'between_all' for _ in list(result_df)]
        result_df.index = [loc_to_site_dict[_] if _ in loc_to_site_dict else 'between_all' for _ in result_df.index.values]
        result_df_heat = result_df.iloc[:, :-1]
        result_df_heat = result_df_heat.where(np.tril(np.ones(result_df_heat.shape)).astype(np.bool))
        heat_map = ax[2].imshow(result_df_heat)
        ax[2].set_xticks(np.arange(len(list(result_df_heat))))
        ax[2].set_yticks(np.arange(len(result_df_heat.index)))
        # ... and label them with the respective list entries
        ax[2].set_xticklabels(list(result_df_heat), rotation='vertical')
        ax[2].set_yticklabels(result_df_heat.index.values)
        plt.colorbar(mappable=heat_map, ax=ax[2])
        # import matplotlib.colors as mcol
        # cm1 = mcol.LinearSegmentedColormap.from_list("MyCmapName", ["b", "r"])
        # sb.heatmap(ax=ax[2], square=True, data=result_df_heat, cmap=cm1)
        # annotate
        for i in range(len(list(result_df_heat))):
            for j in range(len(list(result_df_heat))):
                if result_df_heat.iat[i,j] > 0.4:
                    text = ax[2].text(j, i, f'{stdev_df.iat[i, j]:.2f}',
                                      ha="center", va="center", color="black")
                else:
                    text = ax[2].text(j, i, f'{stdev_df.iat[i, j]:.2f}',
                                   ha="center", va="center", color="w")
        # result_df.plot.bar(ax=ax[2], yerr=stdev_df)

        plt.tight_layout()
        plt.savefig(f's_fig_braycurtis_sqrt.png', dpi=600)
        plt.savefig(f's_fig_braycurtis_sqrt.svg', dpi=600)
    def _set_lims(self, ax):
        # Get the longest side and then set the small side to be the same length
        x_len = ax.get_xlim()[1] - ax.get_xlim()[0]
        y_len = ax.get_ylim()[1] - ax.get_ylim()[0]
        if y_len > x_len:
            # Then the y is the longest and we should adust the x to be bigger
            x_mid = ax.get_xlim()[0] + (x_len / 2)
            x_max = x_mid + (y_len / 2)
            x_min = x_mid - (y_len / 2)
            ax.set_xlim(x_min, x_max)
            ax.set_aspect('equal', 'box')
            return
        else:
            # Then the y is the longest and we should adust the x to be bigger
            y_mid = ax.get_ylim()[0] + (y_len / 2)
            y_max = y_mid + (x_len / 2)
            y_min = y_mid - (x_len / 2)
            ax.set_ylim(y_min, y_max)
            ax.set_aspect('equal', 'box')
            return
Susann()