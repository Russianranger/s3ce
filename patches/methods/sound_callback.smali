.method public onPeriodicNotification(Landroid/media/AudioTrack;)V
    # S3CE: one track generation and serialized lifecycle ownership.
    .locals 4

    monitor-enter p0
    :s3ce_try_start
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-eqz v0, :s3ce_done
    if-ne v0, p1, :s3ce_done
    invoke-virtual {p1}, Landroid/media/AudioTrack;->getPlayState()I
    move-result v1
    const/4 v2, 0x3
    if-ne v1, v2, :s3ce_done
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_SampleData:[S
    iget v1, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_Period:I
    invoke-direct {p0, v0, v1}, Lcom/ideaworks3d/airplay/SoundPlayer;->generateAudio([SI)V
    # Native mixing may reenter stop/pause on this same thread.
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-ne v0, p1, :s3ce_done
    invoke-virtual {p1}, Landroid/media/AudioTrack;->getPlayState()I
    move-result v1
    const/4 v2, 0x3
    if-ne v1, v2, :s3ce_done
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_SampleData:[S
    const/4 v1, 0x0
    iget v2, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_Period:I
    invoke-virtual {p1, v0, v1, v2}, Landroid/media/AudioTrack;->write([SII)I
    :s3ce_done
    :s3ce_try_end
    monitor-exit p0
    return-void
    .catchall {:s3ce_try_start .. :s3ce_try_end} :s3ce_catchall
    :s3ce_catchall
    move-exception v3
    monitor-exit p0
    throw v3
.end method
