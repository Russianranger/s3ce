.method setVolume(I)V
    # S3CE: one track generation and serialized lifecycle ownership.
    .locals 3

    monitor-enter p0
    :s3ce_try_start
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-eqz v0, :s3ce_done
    int-to-float v1, p1
    invoke-static {}, Landroid/media/AudioTrack;->getMaxVolume()F
    move-result v2
    mul-float/2addr v1, v2
    const/high16 v2, 0x42c80000
    div-float/2addr v1, v2
    invoke-virtual {v0, v1, v1}, Landroid/media/AudioTrack;->setStereoVolume(FF)I
    :s3ce_done
    :s3ce_try_end
    monitor-exit p0
    return-void
    .catchall {:s3ce_try_start .. :s3ce_try_end} :s3ce_catchall
    :s3ce_catchall
    move-exception v2
    monitor-exit p0
    throw v2
.end method
