.method resume()V
    # S3CE: one track generation and serialized lifecycle ownership.
    .locals 3

    monitor-enter p0
    :s3ce_try_start
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-eqz v0, :s3ce_done
    invoke-virtual {v0}, Landroid/media/AudioTrack;->getPlayState()I
    move-result v1
    const/4 v2, 0x2
    if-ne v1, v2, :s3ce_done
    const-string v1, "SoundPlayer"
    const-string v2, "resuming sound"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    invoke-virtual {p0}, Lcom/ideaworks3d/airplay/SoundPlayer;->start()V
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
